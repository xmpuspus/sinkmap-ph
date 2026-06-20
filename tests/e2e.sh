#!/bin/zsh
# Behavioral e2e for the sinkmap.ph web map (40 checks) via agent-browser.
# Drives the real map and asserts loading, the sink-lapse slider/play, the flood
# overlays, exposure, place cards, and i18n against window.__diag / window.map / DOM.
#   make serve &              # Range-capable server on :8788
#   tests/e2e.sh              # or: tests/e2e.sh https://sinkmap-ph.vercel.app
set -u
BASE=${1:-http://localhost:8788}
pass=0; fail=0; fails=()

ev(){ agent-browser eval "$1" 2>/dev/null | grep -vE '^$' | tail -1 | tr -d '"' | tr -d ' '; }
chk(){ # name  js  expected(default true)
  local name="$1" js="$2" exp="${3:-true}" got
  got=$(ev "$js")
  if [ "$got" = "$exp" ]; then pass=$((pass+1)); printf 'PASS %s\n' "$name"
  else fail=$((fail+1)); fails+=("$name (got '$got' want '$exp')"); printf 'FAIL %s (got %s want %s)\n' "$name" "$got" "$exp"; fi
}
http(){ # name url expected-code
  local name="$1" code; code=$(curl -s -o /dev/null -w '%{http_code}' "$BASE/$2")
  if [ "$code" = "$3" ]; then pass=$((pass+1)); printf 'PASS %s\n' "$name"
  else fail=$((fail+1)); fails+=("$name ($code)"); printf 'FAIL %s (%s)\n' "$name" "$code"; fi
}

agent-browser open "$BASE" >/dev/null 2>&1
for i in {1..30}; do [ "$(ev 'window.__diag&&window.__diag.ready')" = "true" ] && break; agent-browser wait 500 >/dev/null 2>&1; done

# --- load + diagnostics ---
chk ready "window.__diag.ready"
chk cities_3 "window.__diag.cities===3"
chk layers_3 "window.__diag.layers===3"
chk floods_3 "window.__diag.floods===3"
chk mode_init_rate "window.__diag.mode==='v'"

# --- assets reachable (no 404) ---
http asset_cities "data/cities.json" 200
http asset_velocity "data/velocity/metro-manila.png" 200
http asset_lapse0 "data/lapse/metro-manila/00.png" 200
http asset_lapse7 "data/lapse/metro-manila/07.png" 200
http asset_flood "data/flood-extent/carina-habagat-2024.png" 200
http asset_exposure "data/exposure/metro-manila.geojson" 200
http asset_methodology "methodology.html" 200

# --- map layers present ---
chk basemap "!!map.getLayer('carto')"
chk v_mm "!!map.getLayer('v-metro-manila')"
chk v_cebu "!!map.getLayer('v-cebu-mandaue')"
chk v_iloilo "!!map.getLayer('v-iloilo')"
chk glow_mm "!!map.getLayer('e-metro-manila')"
chk flood_layer "!!map.getLayer('f-carina-habagat-2024')"
chk flood_hidden_init "map.getLayoutProperty('f-carina-habagat-2024','visibility')" none

# --- markers + place cards ---
chk markers_5 "document.querySelectorAll('.pin').length===5"
chk mm_card_opens "(function(){document.querySelectorAll('.pin')[0].click();return document.getElementById('card').style.display})()" block
chk mm_rate_72 "document.getElementById('cd-rate').innerText.indexOf('72')>=0"
chk mm_anchor_109 "document.getElementById('cd-body').innerText.indexOf('109')>=0"
chk mm_flood_41 "document.getElementById('cd-body').innerText.indexOf('41')>=0"
chk mm_exposure "document.getElementById('cd-body').innerText.toLowerCase().indexOf('building')>=0"
chk cebu_card "(function(){document.querySelectorAll('.pin')[1].click();return document.getElementById('cd-body').innerText.toLowerCase().indexOf('reclamation')>=0})()"
chk iloilo_card "(function(){document.querySelectorAll('.pin')[2].click();return document.getElementById('cd-rate').innerText.indexOf('10')>=0})()"
chk limited_card "(function(){document.querySelectorAll('.pin')[3].click();return document.getElementById('cd-body').innerText.toLowerCase().indexOf('coherence')>=0})()"

# --- sink-lapse: load + play ---
chk sink_enter "(function(){document.getElementById('mode-l').click();return window.__diag.mode==='l'})()"
chk sink_starts_2016 "window.__diag.frame===0"
chk sink_overlay_swapped "window.__diag.overlay['metro-manila'].indexOf('lapse')>=0"
chk sink_ctl_visible "document.getElementById('lapse-ctl').style.display" block
chk slider_swaps_frame "(function(){var s=document.getElementById('slider');s.value=3;s.dispatchEvent(new Event('input'));return window.__diag.overlay['metro-manila'].indexOf('/03.png')>=0})()"
chk readout_has_mm "document.getElementById('frame-date').innerText.toLowerCase().indexOf('mm')>=0"
chk glow_hidden_in_sink "map.getLayoutProperty('e-metro-manila','visibility')" none
chk play_starts "(function(){document.getElementById('play').click();return window.__diag.playing})()"
agent-browser wait 2200 >/dev/null 2>&1
chk play_advances "window.__diag.frame>0"
chk play_stops "(function(){document.getElementById('play').click();return window.__diag.playing})()" false
chk rate_restores "(function(){document.getElementById('mode-v').click();return window.__diag.overlay['metro-manila'].indexOf('velocity')>=0})()"
chk glow_restored "map.getLayoutProperty('e-metro-manila','visibility')" visible

# --- flood overlay toggle ---
chk flood_on "(function(){var c=document.querySelectorAll('#flood-toggles input')[0];if(!c.checked)c.click();return map.getLayoutProperty('f-carina-habagat-2024','visibility')})()" visible
chk flood_off "(function(){var c=document.querySelectorAll('#flood-toggles input')[0];if(c.checked)c.click();return map.getLayoutProperty('f-carina-habagat-2024','visibility')})()" none

# --- i18n ---
chk lang_tl "(function(){document.getElementById('tl').click();return document.getElementById('t-sub').innerText.toLowerCase().indexOf('lupa')>=0})()"
chk lang_en "(function(){document.getElementById('en').click();return document.getElementById('t-sub').innerText.toLowerCase().indexOf('ground')>=0})()"

echo "----------------------------------------"
echo "RESULT: $pass passed, $fail failed (of $((pass+fail)))"
if [ $fail -gt 0 ]; then printf '  - %s\n' "${fails[@]}"; exit 1; fi
