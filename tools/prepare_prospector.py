"""Prepare narrowly patched copies of the pinned Prospector sources.

The west checkout stays untouched. Hash checks deliberately fail configuration
when upstream changes, so a dependency update cannot silently skip these fixes.
"""

import argparse
import hashlib
from pathlib import Path


OBSERVER = Path('src/split/bluetooth/central_status_changed_observer.c')
WIDGET = Path('boards/shields/prospector_adapter/src/widgets/battery_bar.c')
HASHES = {
    OBSERVER: 'bda7b09fdd9456fee97ce76d82e5a16099460218ebba6c21a22d848b015ed24f',
    WIDGET: '42d8aca51f791e2e49de6b674de0f3a89586f989256430bd1cf38c72c898d35b',
}


def replace_once(text, before, after):
    if text.count(before) != 1:
        raise ValueError(f'Prospector compatibility patch no longer matches: {before[:80]!r}')
    return text.replace(before, after, 1)


def patch_observer(text):
    # ZMK and Prospector own separate slot arrays. ZMK may already have released
    # its slot when this callback runs; host connections never have a split slot.
    text = replace_once(text, '''static void split_central_process_connection(struct bt_conn *conn) {
    int err;''', '''static void split_central_process_connection(struct bt_conn *conn) {
    int slot_idx = psptr_peripheral_slot_index_for_conn(conn);
    if (slot_idx < 0 || slot_idx >= ZMK_SPLIT_BLE_PERIPHERAL_COUNT) {
        return;
    }''')
    text = replace_once(text, '''.slot = peripheral_slot_index_for_conn(conn),
        .connected = true,''', '''.slot = slot_idx,
        .connected = true,''')
    text = replace_once(text, '''static void split_central_disconnected(struct bt_conn *conn, uint8_t reason) {
    char addr_str[BT_ADDR_LE_STR_LEN];
    int err;''', '''static void split_central_disconnected(struct bt_conn *conn, uint8_t reason) {
    int slot_idx = psptr_peripheral_slot_index_for_conn(conn);
    if (slot_idx < 0 || slot_idx >= ZMK_SPLIT_BLE_PERIPHERAL_COUNT) {
        return;
    }
    char addr_str[BT_ADDR_LE_STR_LEN];''')
    text = replace_once(text, '''.slot = peripheral_slot_index_for_conn(conn),
        .connected = false,''', '''.slot = slot_idx,
        .connected = false,''')
    return replace_once(text, '''    // k_msleep(100);

    err = release_psptr_peripheral_slot_for_conn(conn);

    if (err < 0) {
        return;
    }''', '''    release_psptr_peripheral_slot(slot_idx);''')


def patch_widget(text):
    # Validate the whole destination before any LVGL mutation.
    for function, state_type in [('set_battery_bar_value', 'battery_update_state'),
                                  ('set_battery_bar_connected', 'connection_update_state')]:
        before = f'''static void {function}(lv_obj_t *widget, struct {state_type} state) {{
    if (initialized) {{
        lv_obj_t *info_container = lv_obj_get_child(widget, state.source);'''
        after = f'''static void {function}(lv_obj_t *widget, struct {state_type} state) {{
    if (initialized && widget != NULL && state.source < ZMK_SPLIT_BLE_PERIPHERAL_COUNT) {{
        lv_obj_t *info_container = lv_obj_get_child(widget, state.source);
        if (info_container == NULL) {{
            return;
        }}'''
        text = replace_once(text, before, after)
    text = replace_once(text, '''        lv_bar_set_value(bar, state.level, LV_ANIM_ON);''', '''        if (bar == NULL || num == NULL) {
            return;
        }
        lv_bar_set_value(bar, state.level, LV_ANIM_ON);''')
    text = replace_once(text, '''        LOG_DBG("Peripheral %d %s", state.source,''', '''        if (bar == NULL || num == NULL || nc_bar == NULL || nc_num == NULL) {
            return;
        }
        LOG_DBG("Peripheral %d %s", state.source,''')
    # ZMK_DISPLAY_WIDGET_LISTENER calls these getters with NULL during init.
    # An invalid source represents "no event" and is ignored by both setters.
    for function, state_type, event in [
        ('battery_bar_get_battery_state', 'battery_update_state', 'bat_ev'),
        ('battery_bar_get_connection_state', 'connection_update_state', 'conn_ev'),
    ]:
        signature = f'static struct {state_type} {function}(const zmk_event_t *eh) {{'
        text = replace_once(text, signature, signature + f'''
    if (eh == NULL) {{
        return (struct {state_type}){{.source = UINT8_MAX}};
    }}''')
        cast = ('as_zmk_peripheral_battery_state_changed(eh);' if event == 'bat_ev'
                else 'as_zmk_split_central_status_changed(eh);')
        text = replace_once(text, cast, cast + f'''
    if ({event} == NULL) {{
        return (struct {state_type}){{.source = UINT8_MAX}};
    }}''')
    return text


def prepare(source_dir, output_dir):
    patched = {}
    for path, expected in HASHES.items():
        data = (source_dir / path).read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise ValueError(f'Unsupported Prospector source: {path}; review compatibility fixes before updating the dependency')
        patched[path] = (patch_observer if path == OBSERVER else patch_widget)(data.decode())
    for path, text in patched.items():
        destination = output_dir / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(text)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-dir', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    prepare(args.source_dir, args.output_dir)
