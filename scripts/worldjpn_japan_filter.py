"""Which World and Japan documents count as Japan-related (shared by worldjpn_list.py and the review below)."""
import re
# indexes whose every entry is a Japanese government speech or decision; the other indexes (including "prewar Japanese
# politics and diplomacy" and "Japan security policy") also carry purely international background documents
ALWAYS = {"Prime Ministers' speeches", "Foreign Ministers' speeches", "Finance Ministers' speeches", "Economy Ministers' speeches",
          'Other speeches by Prime Ministers', 'Other speeches by Foreign Ministers', 'Cabinet decisions and important policies',
          'Japanese speeches at the UN General Assembly',
          # Japanese initiatives and policy, and East Asian relations: every entry reviewed as Japan- or East Asia-related
          'TICAD documents', "Japan's history issues", 'Free and Open Indo-Pacific documents', 'Pacific Islands Leaders Meetings',
          'Japan-China-Korea relations', 'Japan-Korean Peninsula relations', 'Japan-China relations', 'Japan-Taiwan relations',
          'Japan-Mongolia relations', 'Japan-Southeast Asia relations', 'Japan security policy'}
# entries of those indexes that are not Japanese after all (reviewed by hand)
EXCLUDE_URLS = set()
# not Japanese, but kept on request (the user, 2026-10-14: "leave the treaty of nanking")
KEEP_URLS = {'https://worldjpn.net/documents/texts/pw/18420829.T1E.html',
    # kept after reading the drop list by hand (Japan or East Asia, but nothing in the title says so)
    'https://worldjpn.net/documents/texts/docs/20080528.T1E.html',
    'https://worldjpn.net/documents/texts/docs/20130125.O1E.html',
    'https://worldjpn.net/documents/texts/PI/20220323.O1E.html',
    'https://worldjpn.net/documents/texts/PI/20220324.O2E.html',
    'https://worldjpn.net/documents/texts/pw/18991220.O1E.html',
    'https://worldjpn.net/documents/texts/pw/19220206.T1E.html',
    'https://worldjpn.net/documents/texts/docs/19280827.T1E.html',
    'https://worldjpn.net/documents/texts/JPUS/19510905.S1E.html',
    'https://worldjpn.net/documents/texts/JPSA/19530424.T1E.html',
    'https://worldjpn.net/documents/texts/JPUS/19540308.O1E.html',
    'https://worldjpn.net/documents/texts/docs/19690725.O1E.html',
    'https://worldjpn.net/documents/texts/JPUS/19850102.O2E.html',
    'https://worldjpn.net/documents/texts/JPUS/19880113.O1E.html',
    'https://worldjpn.net/documents/texts/JPEU/19950529.O1E.html',
    'https://worldjpn.net/documents/texts/JPME/20060206.O2E.html',
    'https://worldjpn.net/documents/texts/JPUS/20090425.O2E.html',
    'https://worldjpn.net/documents/texts/JPUS/20091114.S1E.html',
    'https://worldjpn.net/documents/texts/JPEU/20120410.O1E.html',
    'https://worldjpn.net/documents/texts/PI/20201109.S1E.html',
    'https://worldjpn.net/documents/texts/PI/20201109.O1E.html',
    'https://worldjpn.net/documents/texts/PI/20201112.O1E.html',
    'https://worldjpn.net/documents/texts/PI/20220301.O1E.html',
    'https://worldjpn.net/documents/texts/PI/20220309.O1E.html',
    'https://worldjpn.net/documents/texts/PI/20220426.O2E.html',
    'https://worldjpn.net/documents/texts/PI/20220504.O2E.html',
    'https://worldjpn.net/documents/texts/PI/20221004.O3E.html',
    'https://worldjpn.net/documents/texts/JPEU/20240219.D1E.html',
    'https://worldjpn.net/documents/texts/JPPC/20260504.D5E.html',
}
KW = re.compile(r"japan|nippon|tokyo|kyoto|osaka|hiroshima|nagasaki|okinawa|ryukyu|imperial rescript|potsdam|cairo declaration|yalta|"
                r"instrument of surrender|connection with surrender|hull note|supreme commander|scap|macarthur|manchu|kanagawa|shimonoseki|portsmouth|shimoda|yedo|showa|meiji|"
                r"mikado|emperor of japan|\b(abe|koizumi|kishida|fukuda|nakasone|takeshita|kaifu|miyazawa|hosokawa|murayama|hashimoto|obuchi|"
                r"mori|aso|hatoyama|noda|suga|ishiba|ikeda|sato|tanaka|miki|ohira|yoshida|kishi|okada|kono|gemba|motegi|hayashi|kamikawa|"
                r"iwaya|takaichi|shigemitsu|matsuoka|konoe|konoye|tojo|hirota|arita|togo|nomura|kurusu|shidehara|katsura|komura|mutsu|okuma|"
                r"ogata|toyako|ise-shima|kobe|niigata|kitakyushu|kurashiki|toyama|tsukuba|yokohama|sendai|nagoya|sapporo|fukuoka|hokkaido|karuizawa|"
                r"inukai|saito|uchida|ishii|amau|amo|kato|yamagata|ito hirobumi|terauchi|hara)\b|senkaku|takeshima|northern territories|habomai|shikotan", re.I)
JKW = re.compile(r"日本|日米|日中|日露|日英|日韓|日朝|日ソ|日独|日仏|日蘭|日清|日タイ|日満|日華|日印|日豪|日比|日越|日・|日ASEAN|日EU|"
                 r"日アフリカ|日墨|日伯|日加|対日|大日本|帝國|ポツダム|降伏|聯合國最高|連合国最高|マッカーサー|総理|首相|外相|外務大臣|天皇|"
                 r"我が国|わが国|尖閣|竹島|北方領土|沖縄|琉球|満洲|満州")
# East and Southeast Asia: kept as well (the user, 2026-10-14: "leave any related to east or southeast asia")
EA = re.compile(r"china|chinese|peking|beijing|nanking|nanjing|tientsin|tianjin|canton|shanghai|hong ?kong|macao|macau|taiwan|formosa|"
                r"korea|corea|dprk|pyongyang|seoul|manchu|mongol|siam|thai|viet|indo-?china|cambodia|laos|lao |burma|myanmar|malay|"
                r"singapore|indonesia|philippine|manila|brunei|timor|asean|east asia|asia|pacific|nerchinsk|kiakhta|ta-tsing|wang-?hea|"
                r"wanghia|bogue|kuomintang|chiang|mao|zhou|deng|six-party|mekong", re.I)
EAJ = re.compile(r"中国|中華|清|支那|朝鮮|韓国|韓|台湾|臺灣|満|蒙古|モンゴル|タイ|シャム|暹羅|越南|ベトナム|ヴィエトナム|インドシナ|カンボジア|"
                 r"ラオス|ビルマ|ミャンマー|マレー|シンガポール|インドネシア|フィリピン|比律賓|ブルネイ|東ティモール|ASEAN|東アジア|アジア|太平洋|"
                 r"南京|天津|北京|上海|香港|澳門|マカオ|ネルチンスク|キャフタ|恰克|尼布楚|江寧|望厦")
def east_asia(d):
    return bool(EA.search(d['title_en'] or '')) or bool(EAJ.search(d['title_ja'] or ''))
import json as _json, os as _os
_OV = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), 'index', 'worldjpn_overrides.json')
OVERRIDES = _json.load(open(_OV)) if _os.path.exists(_OV) else {}   # corrections made by hand (titles, keep, exclude)
def japan_related(d):
    o = OVERRIDES.get(d['url'], {})
    if d['url'] in EXCLUDE_URLS or o.get('exclude'): return False
    if o.get('keep'): return True
    return d['url'] in KEEP_URLS or east_asia(d) or bool(set(d['indices']) & ALWAYS) or bool(KW.search(d['title_en'] or '')) or bool(JKW.search(d['title_ja'] or ''))
