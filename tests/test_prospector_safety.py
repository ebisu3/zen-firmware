"""Run the actual Prospector C handlers with small BLE/LVGL boundary fakes.

Usage: python3 tests/test_prospector_safety.py
Downloads the pinned sources and tests the generated compatibility fixes.
Use --source-dir <module-or-patched-dir> to test existing C sources directly.
"""

import argparse
import importlib.util
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest
import urllib.request

parser = argparse.ArgumentParser()
parser.add_argument('--source-dir', type=Path, help='Test supplied C sources directly, without preparing fixes')
args, unittest_args = parser.parse_known_args()

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('prepare_prospector', ROOT / 'tools/prepare_prospector.py')
compat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(compat)
source_cache = None
if args.source_dir is None:
    source_cache = tempfile.TemporaryDirectory()
    original_dir = Path(source_cache.name) / 'upstream'
    module = (ROOT / 'config/west.yml').read_text().split('- name: prospector-zmk-module\n', 1)[1]
    revision = re.search(r'^\s+revision: ([0-9a-f]{40})$', module, re.M).group(1)
    for relative in compat.HASHES:
        destination = original_dir / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        url = f'https://raw.githubusercontent.com/carrefinho/prospector-zmk-module/{revision}/{relative}'
        with urllib.request.urlopen(url, timeout=30) as response:
            destination.write_bytes(response.read())
    args.source_dir = Path(source_cache.name) / 'patched'
    compat.prepare(original_dir, args.source_dir)


def function(source, name):
    """Extract the implementation under test, not a reimplementation of it."""
    marker = name + '('
    start = source.index(marker)
    start = source.rfind('\n', 0, start) + 1
    brace = source.index('{', start)
    depth = 1
    for end in range(brace + 1, len(source)):
        depth += (source[end] == '{') - (source[end] == '}')
        if depth == 0:
            return source[start:end + 1]
    raise ValueError(name)


BOUNDARIES = r'''
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <errno.h>
#define ZMK_SPLIT_BLE_PERIPHERAL_COUNT 2
#define BT_ADDR_LE_STR_LEN 32
#define BT_CONN_ROLE_CENTRAL 0
#define BT_CONN_ROLE_PERIPHERAL 1
#define LOG_DBG(...) ((void)0)
#define LOG_ERR(...) ((void)0)
#define IS_ENABLED(x) 0
#define LV_ANIM_ON 1
#define LV_PART_INDICATOR 1
#define LV_PART_MAIN 0
struct bt_conn { int id; int role; int core_slot; };
struct bt_conn_le_phy_info { int rx_phy; };
struct bt_conn_info { int role; struct { int interval, latency; struct bt_conn_le_phy_info *phy; } le; };
enum psptr_peripheral_slot_state { PERIPHERAL_SLOT_STATE_OPEN, PERIPHERAL_SLOT_STATE_CONNECTING, PERIPHERAL_SLOT_STATE_CONNECTED };
struct psptr_peripheral_slot { enum psptr_peripheral_slot_state state; struct bt_conn *conn; };
static struct psptr_peripheral_slot peripherals[2];
struct zmk_split_central_status_changed { uint8_t slot; bool connected; };
static int emitted;
static struct zmk_split_central_status_changed last;
static void raise_zmk_split_central_status_changed(struct zmk_split_central_status_changed event) { ++emitted; last = event; }
static int peripheral_slot_index_for_conn(struct bt_conn *conn) { return conn->core_slot; }
static int bt_conn_get_info(struct bt_conn *conn, struct bt_conn_info *info) { static struct bt_conn_le_phy_info phy; *info=(struct bt_conn_info){.role=conn->role,.le={.phy=&phy}}; return 0; }
static int bt_conn_get_security(struct bt_conn *conn) { return 4; }
static const struct bt_conn *bt_conn_get_dst(struct bt_conn *conn) { return conn; }
static int zmk_ble_put_peripheral_addr(const struct bt_conn *addr) { return addr->id; }
static void bt_addr_le_to_str(const struct bt_conn *addr, char *text, size_t size) { if(size) text[0]=0; }
typedef struct lv_obj { struct lv_obj *children[4]; unsigned count; int value; bool visible; } lv_obj_t;
static bool initialized = true;
static int invalid_access;
static lv_obj_t *lv_obj_get_child(lv_obj_t *parent, int index) { if(!parent) { ++invalid_access; return NULL; } return index>=0 && (unsigned)index<parent->count ? parent->children[index] : NULL; }
static void lv_obj_fade_in(lv_obj_t *obj, int duration, int delay) { if(!obj) ++invalid_access; else obj->visible=true; }
static void lv_obj_fade_out(lv_obj_t *obj, int duration, int delay) { if(!obj) ++invalid_access; else obj->visible=false; }
static void lv_bar_set_value(lv_obj_t *obj, int value, int animation) { if(!obj) ++invalid_access; else obj->value=value; }
static void lv_label_set_text_fmt(lv_obj_t *obj, const char *format, int value) { if(!obj) ++invalid_access; else obj->value=value; }
static int lv_color_hex(unsigned color) { return (int)color; }
static void lv_obj_set_style_bg_color(lv_obj_t *obj, int color, int part) { if(!obj) ++invalid_access; }
static void lv_obj_set_style_bg_grad_color(lv_obj_t *obj, int color, int part) { if(!obj) ++invalid_access; }
static void lv_obj_set_style_text_color(lv_obj_t *obj, int color, int part) { if(!obj) ++invalid_access; }
struct battery_update_state { uint8_t source, level; };
struct connection_update_state { uint8_t source; bool connected; };
struct zmk_peripheral_battery_state_changed { uint8_t source, state_of_charge; };
typedef struct { int kind; struct zmk_peripheral_battery_state_changed battery; struct zmk_split_central_status_changed connection; } zmk_event_t;
static const struct zmk_peripheral_battery_state_changed *as_zmk_peripheral_battery_state_changed(const zmk_event_t *event) { return event && event->kind==1 ? &event->battery : NULL; }
static const struct zmk_split_central_status_changed *as_zmk_split_central_status_changed(const zmk_event_t *event) { return event && event->kind==2 ? &event->connection : NULL; }
'''

CASES = r'''
#define REQUIRE(condition) do { if(!(condition)) { fprintf(stderr,"failed: %s\n",#condition); return 1; } } while(0)
int main(int argc, char **argv) {
    int scenario=atoi(argv[1]);
    struct bt_conn left={.id=0,.role=BT_CONN_ROLE_CENTRAL,.core_slot=0};
    struct bt_conn right={.id=1,.role=BT_CONN_ROLE_CENTRAL,.core_slot=1};
    struct bt_conn host={.id=-1,.role=BT_CONN_ROLE_PERIPHERAL,.core_slot=-EINVAL};
    lv_obj_t root={.count=2}, info[2]={{.count=4},{.count=4}}, parts[2][4]={0};
    for(int i=0;i<2;++i) { root.children[i]=&info[i]; for(int j=0;j<4;++j) info[i].children[j]=&parts[i][j]; }
    if(scenario==0) {
        split_central_disconnected(&host,0);
        REQUIRE(emitted==0);
    } else if(scenario==1 || scenario==2) {
        struct bt_conn *conn=scenario==1 ? &left : &right;
        int slot=conn->id;
        REQUIRE(reserve_psptr_peripheral_slot_for_conn(conn)==slot);
        conn->core_slot=-EINVAL; /* ZMK has already released its independent slot. */
        split_central_disconnected(conn,0);
        REQUIRE(emitted==1 && last.slot==slot && !last.connected);
        REQUIRE(peripherals[slot].state==PERIPHERAL_SLOT_STATE_OPEN);
        REQUIRE(reserve_psptr_peripheral_slot_for_conn(conn)==slot);
        split_central_process_connection(conn);
        REQUIRE(emitted==2 && last.slot==slot && last.connected);
    } else if(scenario==3) {
        split_central_process_connection(&host);
        REQUIRE(emitted==0);
    } else if(scenario==4) {
        set_battery_bar_connected(&root,(struct connection_update_state){.source=234,.connected=false});
        REQUIRE(invalid_access==0);
        REQUIRE(!parts[0][0].visible && !parts[1][0].visible);
    } else if(scenario==5) {
        set_battery_bar_value(&root,(struct battery_update_state){.source=255,.level=80});
        REQUIRE(invalid_access==0 && parts[0][0].value==0 && parts[1][0].value==0);
    } else if(scenario==6) {
        root.children[1]=NULL;
        set_battery_bar_connected(&root,(struct connection_update_state){.source=1,.connected=true});
        REQUIRE(invalid_access==0);
    } else if(scenario==7) {
        info[1].children[3]=NULL;
        set_battery_bar_connected(&root,(struct connection_update_state){.source=1,.connected=true});
        REQUIRE(invalid_access==0 && !parts[1][0].visible);
    } else if(scenario==8) {
        set_battery_bar_connected(&root,(struct connection_update_state){.source=1,.connected=true});
        REQUIRE(invalid_access==0 && parts[1][0].visible && parts[1][1].visible);
        REQUIRE(!parts[1][2].visible && !parts[1][3].visible && !parts[0][0].visible);
        set_battery_bar_connected(&root,(struct connection_update_state){.source=1,.connected=false});
        REQUIRE(!parts[1][0].visible && !parts[1][1].visible && parts[1][2].visible && parts[1][3].visible);
    } else if(scenario==9) {
        set_battery_bar_value(&root,(struct battery_update_state){.source=1,.level=77});
        REQUIRE(invalid_access==0 && parts[1][0].value==77 && parts[1][1].value==77 && parts[0][0].value==0);
    } else if(scenario==10) {
        struct battery_update_state state=battery_bar_get_battery_state(NULL);
        REQUIRE(state.source>=2);
    } else if(scenario==11) {
        struct connection_update_state state=battery_bar_get_connection_state(NULL);
        REQUIRE(state.source>=2);
    } else if(scenario==12) {
        zmk_event_t event={.kind=1,.battery={.source=1,.state_of_charge=77}};
        struct battery_update_state state=battery_bar_get_battery_state(&event);
        REQUIRE(state.source==1 && state.level==77);
    } else if(scenario==13) {
        zmk_event_t event={.kind=2,.connection={.slot=0,.connected=true}};
        struct connection_update_state state=battery_bar_get_connection_state(&event);
        REQUIRE(state.source==0 && state.connected);
    } else if(scenario==14) {
        set_battery_bar_connected(NULL,(struct connection_update_state){.source=0,.connected=true});
        set_battery_bar_value(NULL,(struct battery_update_state){.source=0,.level=77});
        REQUIRE(invalid_access==0);
    } else if(scenario==15) {
        info[1].children[1]=NULL;
        set_battery_bar_value(&root,(struct battery_update_state){.source=1,.level=77});
        REQUIRE(invalid_access==0 && parts[1][0].value==0);
    }
    return 0;
}
'''


class ProspectorSafety(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        observer = (args.source_dir / 'src/split/bluetooth/central_status_changed_observer.c').read_text()
        widget = (args.source_dir / 'boards/shields/prospector_adapter/src/widgets/battery_bar.c').read_text()
        observer_names = ['psptr_peripheral_slot_index_for_conn', 'psptr_peripheral_slot_for_conn', 'release_psptr_peripheral_slot', 'reserve_psptr_peripheral_slot_for_conn', 'release_psptr_peripheral_slot_for_conn', 'split_central_process_connection', 'split_central_disconnected']
        widget_names = ['set_battery_bar_value', 'set_battery_bar_connected', 'battery_bar_get_battery_state', 'battery_bar_get_connection_state']
        program = BOUNDARIES + '\n'.join(function(observer,n) for n in observer_names) + '\n'.join(function(widget,n) for n in widget_names) + CASES
        source = Path(cls.temp.name) / 'handlers.c'
        source.write_text(program)
        cls.executable = Path(cls.temp.name) / 'handlers'
        compiler = shutil.which('cc') or shutil.which('clang')
        if not compiler:
            raise RuntimeError('A native C compiler is required')
        subprocess.run([compiler, '-std=c11', '-Wall', '-Wextra', '-Wno-unused-variable', '-Wno-unused-function', '-Wno-unused-parameter', str(source), '-o', str(cls.executable)], check=True, capture_output=True, text=True)

    def run_case(self, scenario):
        result = subprocess.run([str(self.executable), str(scenario)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr or f'handler exited {result.returncode}')


@unittest.skipIf(source_cache is None, 'Direct source test mode does not prepare sources')
class CompatibilityPreparation(unittest.TestCase):
    def test_preparation_does_not_modify_west_checkout(self):
        import hashlib
        for relative, digest in compat.HASHES.items():
            self.assertEqual(hashlib.sha256((original_dir / relative).read_bytes()).hexdigest(), digest)

    def test_changed_dependency_is_rejected_before_writing(self):
        with tempfile.TemporaryDirectory() as temp:
            changed = Path(temp) / 'changed'
            shutil.copytree(original_dir, changed)
            widget = changed / compat.WIDGET
            widget.write_bytes(widget.read_bytes() + b'\n/* changed upstream */\n')
            output = Path(temp) / 'output'
            with self.assertRaisesRegex(ValueError, 'Unsupported Prospector source'):
                compat.prepare(changed, output)
            self.assertFalse(output.exists())


SCENARIOS = [
    'host_disconnect_emits_no_peripheral_event',
    'left_disconnect_and_reconnect_survive_core_slot_release',
    'right_disconnect_and_reconnect_survive_core_slot_release',
    'untracked_connection_emits_no_status',
    'out_of_range_connection_source_does_not_touch_widgets',
    'out_of_range_battery_source_does_not_touch_widgets',
    'missing_connection_container_is_ignored',
    'missing_connection_child_does_not_partially_update_widgets',
    'valid_connection_and_disconnect_update_only_the_target_side',
    'valid_battery_update_changes_only_the_target_side',
    'null_initial_battery_event_returns_no_update',
    'null_initial_connection_event_returns_no_update',
    'valid_battery_event_preserves_source_and_charge',
    'valid_connection_event_preserves_source_and_state',
    'null_widgets_are_ignored',
    'missing_battery_child_does_not_partially_update_widgets',
]
for number, name in enumerate(SCENARIOS):
    def case(self, scenario=number):
        self.run_case(scenario)
    setattr(ProspectorSafety, 'test_' + name, case)

if __name__ == '__main__':
    try:
        unittest.main(argv=[__file__, *unittest_args])
    finally:
        if source_cache is not None:
            source_cache.cleanup()
