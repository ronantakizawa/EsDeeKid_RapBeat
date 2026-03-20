"""
fetch_freesound.py — Download EsDeeKid-relevant samples from Freesound.org
===========================================================================
Gets a free API key at: https://freesound.org/apiv2/apply/
Then run:  python fetch_freesound.py <YOUR_API_KEY>

Downloads samples into:
  /Users/ronantakizawa/Documents/instruments/Freesound/<category>/
"""

import sys
import os
import time
import freesound

OUTPUT_BASE = '/Users/ronantakizawa/Documents/instruments/Freesound'

# Searches to run: (folder_name, query, filter, max_results)
SEARCHES = [
    ('kicks_dark',    'dark distorted kick drum',      'tag:kick duration:[0.1 TO 1.5]',    10),
    ('kicks_heavy',   'heavy 808 kick',                'tag:kick tag:bass duration:[0.1 TO 2]', 8),
    ('snares_crack',  'snare crack hit',               'tag:snare duration:[0.05 TO 1.0]',  12),
    ('snares_snap',   'snare snap punch',              'tag:snare duration:[0.05 TO 0.8]',  10),
    ('hihats_closed', 'closed hi hat tight',           'tag:hihat duration:[0.02 TO 0.5]',  10),
    ('hihats_open',   'open hi hat',                   'tag:hihat duration:[0.1 TO 1.5]',    8),
    ('808_bass',      '808 bass hit sub',              'tag:808 duration:[0.5 TO 4.0]',      8),
    ('fx_riser',      'riser whoosh dark',             'tag:riser duration:[1.0 TO 6.0]',    6),
    ('fx_impact',     'impact hit boom dark',          'duration:[0.1 TO 2.0]',              8),
    ('vocal_chop',    'vocal chop hit dark',           'tag:vocal duration:[0.1 TO 2.0]',    8),
    ('perc_metal',    'metallic percussion hit',       'tag:percussion duration:[0.05 TO 1]',8),
    ('crash_dark',    'dark crash cymbal',             'tag:cymbal tag:crash duration:[0.5 TO 4]', 6),
]


def search_and_download(client, folder, query, filt, max_results):
    out_dir = os.path.join(OUTPUT_BASE, folder)
    os.makedirs(out_dir, exist_ok=True)

    print(f'\n  [{folder}]  "{query}"')
    try:
        results = client.text_search(
            query=query,
            filter=filt + ' type:wav',
            sort='rating_desc',
            fields='id,name,duration,license,previews',
            page_size=min(max_results, 15),
        )
    except Exception as e:
        print(f'    Search failed: {e}')
        return 0

    downloaded = 0
    for sound in results:
        if downloaded >= max_results:
            break
        fname = f'{sound.id}_{sound.name[:40].replace("/","_")}.wav'
        fpath = os.path.join(out_dir, fname)
        if os.path.exists(fpath):
            print(f'    skip (exists): {fname}')
            downloaded += 1
            continue
        try:
            sound.retrieve(out_dir, name=fname)
            print(f'    ✓ {sound.duration:.2f}s  {fname}')
            downloaded += 1
            time.sleep(0.3)   # be polite to the API
        except Exception as e:
            print(f'    ✗ {fname}: {e}')

    return downloaded


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    api_key = sys.argv[1]
    client  = freesound.FreesoundClient()
    client.set_token(api_key, 'token')

    print(f'Freesound sample downloader')
    print(f'Output: {OUTPUT_BASE}')
    print(f'Searches: {len(SEARCHES)}')

    total = 0
    for folder, query, filt, max_r in SEARCHES:
        total += search_and_download(client, folder, query, filt, max_r)

    print(f'\n✓ Done — {total} samples downloaded to {OUTPUT_BASE}')
    print('\nTo use in render_rap.py, add paths like:')
    print(f"  KICKS += [load_sample(p) for p in glob('{OUTPUT_BASE}/kicks_dark/*.wav')]")


if __name__ == '__main__':
    main()
