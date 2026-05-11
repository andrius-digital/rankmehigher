"""Audio mastering presets for UGC reels.

Importable filter-chain builders that return the ffmpeg filter_complex parts
needed to master a reel's voice + music tracks into a broadcast-style output.

Add a new preset by writing a new function that takes (voice_idx, music_idx)
and returns (parts: list[str], output_label: str). The reel script appends
`parts` to its filter_complex and maps `[<output_label>]` as the audio out.
"""

from __future__ import annotations


def broadcast_ad_chain(
    voice_idx: int,
    music_idx: int,
    music_base_volume: float = 0.50,
) -> tuple[list[str], str]:
    """Broadcast-ad mastering: vocal forward, music ducked, -14 LUFS final.

    Sounds like a real TV/radio ad — voice sits clearly in front, music
    fills behind in the gaps, overall loudness matches IG/TikTok/YouTube
    streaming targets so the reel doesn't feel quiet on the feed.

    Voice chain:
      - HPF 80 Hz (kill rumble)
      - EQ: −2 dB @ 250 Hz (cut mud), +2.5 dB @ 3 kHz (presence/forward),
            +1.5 dB @ 12 kHz (air)
      - 3:1 glue compression at −18 dB threshold + 3 dB makeup gain
      - Split: one copy goes to the mix, one copy triggers the sidechain

    Music chain:
      - EQ: −3 dB @ 200 Hz, −2 dB @ 3 kHz (carve vocal pocket so the voice
        cuts through without fighting the music)
      - Base volume scaling
      - Sidechain compression keyed by voice: when voice plays, music ducks
        ~4-6 dB; when voice pauses, music comes back up. This is the single
        biggest "feels professional" trick in ad audio.

    Mix:
      - 2:1 glue compression to gel voice + music
      - True-peak limiter at −1 dBTP
      - Loudness normalization to -14 LUFS (Spotify / IG / TikTok / YouTube
        target). Broadcast TV ads sit louder, around -10 to -12, but -14
        is the safer cross-platform choice for social-first reels.

    Returns:
        (parts, output_label) where output_label is the named link to map
        as the final audio stream (e.g. `-map "[outa]"`).
    """
    parts = [
        # Voice: HPF, EQ for presence + air, glue compression, split for sidechain
        f"[{voice_idx}:a]"
        f"highpass=f=80,"
        f"equalizer=f=250:t=q:w=2:g=-2,"
        f"equalizer=f=3000:t=q:w=1.5:g=2.5,"
        f"equalizer=f=12000:t=q:w=1:g=1.5,"
        # Lighter glue compression (2:1, less makeup) — keeps natural dynamics so
        # the voice doesn't sound squashed/robotic. The earlier 3:1 + 3 dB makeup
        # was too aggressive.
        f"acompressor=threshold=-20dB:ratio=2:attack=8:release=120:makeup=2,"
        f"asplit=2[v_main][v_sc]",

        # Music: EQ to carve vocal pocket + base level, padded to cover voice length
        f"[{music_idx}:a]"
        f"equalizer=f=200:t=q:w=2:g=-3,"
        f"equalizer=f=3000:t=q:w=1.5:g=-2,"
        f"volume={music_base_volume},apad[music_eq]",

        # Sidechain duck: music dips when voice plays. ffmpeg's makeup
        # param has a minimum of 1, so we use 1 (no makeup gain) instead
        # of 0. Compensate elsewhere in the music_base_volume if needed.
        f"[music_eq][v_sc]"
        f"sidechaincompress=threshold=0.04:ratio=5:attack=10:release=300:makeup=1"
        f"[music_ducked]",

        # Mix + master: light bus compression, true-peak limit, -14 LUFS final
        f"[v_main][music_ducked]"
        f"amix=inputs=2:duration=first:dropout_transition=0,"
        f"acompressor=threshold=-12dB:ratio=1.5:attack=15:release=250:makeup=1,"
        f"alimiter=limit=0.95,"
        f"loudnorm=I=-14:LRA=11:TP=-1[outa]",
    ]
    return parts, "outa"
