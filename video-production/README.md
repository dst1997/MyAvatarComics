# Preschool AI Video Pilot Workflow

This folder implements the lean pilot workflow for preschool-friendly AI videos.
It is intentionally separate from the comic app. Use it to plan, produce, review,
and manually upload one short video per week during the first pilot month.

## Pilot Defaults

| Item | Default |
| --- | --- |
| Cadence | 1 video per week for 4 weeks |
| Budget | Lean pilot, about $57-100/month before tax and regional differences |
| Runtime | 60-90 seconds |
| Audience | Preschool, simple English, ages 3-4 |
| Content pillar | Life skills stories |
| Visual style | Soft 3D storybook animation |
| Characters | Original fictional characters only |
| Audio | Warm adult narrator, gentle music, light sound effects |
| Publishing | Manual upload in YouTube Studio, set as Made for Kids |

## Recommended Tool Stack

- Video clips: Runway Pro first. Use mostly Gen-4 Turbo style generations and
  reserve more expensive models for opening shots, thumbnails, or hard shots.
- Voice/music/SFX: ElevenLabs Starter first. Upgrade only if narration, music,
  or sound effects credits become the bottleneck.
- Editing: CapCut Desktop or DaVinci Resolve free.
- Upload: YouTube Studio on desktop so the Made for Kids and AI-use settings can
  be reviewed manually.

Prices and plan limits change. Recheck vendor pricing before subscribing.

## Weekly Workflow

1. Pick one everyday preschool lesson: sharing, brushing teeth, waiting, saying
   sorry, asking for help, bedtime, cleaning up, or naming feelings.
2. Create the episode package:

   ```powershell
   python scripts/create_episode_package.py "Kind Hands" --lesson "sharing toys" --date 2026-07-06
   ```

3. Fill in `brief.md`, then write a 90-140 word narration in `script.md`.
4. Build a 5-7 shot list. Keep shots simple, bright, and easy to understand.
5. Generate each AI video clip with a maximum of 2 retries per shot. Log every
   accepted and rejected attempt in `clip-log.csv`.
6. Generate narration, music, and sound effects. Keep the narrator calm and the
   mix gentle.
7. Edit the final video to 60-90 seconds.
8. Complete `upload-checklist.md` before uploading.
9. Upload manually to YouTube Studio, set the audience to Made for Kids, and set
   AI use according to YouTube's current disclosure flow.

## Free Local Prototype

For a $0 first draft, render a captioned local prototype instead of using paid
AI video or voice tools:

```powershell
python scripts\render_free_preschool_video.py
```

The free renderer creates a simple original soft-storybook MP4, thumbnail,
narration text, and notes under `test-output/free-preschool-video/`. It uses
local Python drawing plus OpenCV video encoding, so it has no paid AI clips and
no paid voiceover. Record the narration manually or add a free voiceover later
in CapCut or DaVinci Resolve.

## Creative Rules

- Use original characters and original settings. Do not use famous characters,
  brands, logos, toys, or real child likenesses.
- Keep the conflict small and safe: a child-friendly mistake, feeling, or
  problem that gets resolved kindly.
- Keep language simple. Prefer short sentences and everyday vocabulary.
- Do not ask children to like, subscribe, buy, click, download, comment, or tell
  parents to purchase anything.
- Avoid scary sounds, jump cuts, intense chase scenes, weapons, dangerous
  actions, humiliating jokes, bullying, product packaging, and shopping focus.
- Do not keyword-stuff titles, descriptions, or thumbnails.

## Export Settings

- Container: MP4
- Aspect ratio: 16:9
- Resolution: 1920x1080
- Frame rate: 30 fps
- Video codec: H.264, progressive scan
- Audio codec: AAC, stereo, 48 kHz
- Target upload bitrate: 8 Mbps or higher for 1080p SDR

## Pilot Review After 4 Videos

After four published videos, complete `four-video-review.md`. Decide whether to:

- keep 1 video per week,
- scale to 2 videos per week,
- upgrade Runway,
- upgrade ElevenLabs,
- create a permanent show/channel brand,
- or change the creative format.

## Policy And Tool References

- YouTube Made for Kids: https://support.google.com/youtube/answer/9528076
- YouTube Kids policies: https://support.google.com/youtube/answer/10938174
- YouTube upload encoding: https://support.google.com/youtube/answer/1722171
- YouTube AI disclosure: https://support.google.com/youtube/answer/14328491
- Runway pricing: https://runwayml.com/pricing
- Runway Gen-4 consistency: https://runwayml.com/research/introducing-runway-gen-4
- ElevenLabs pricing: https://elevenlabs.io/pricing
