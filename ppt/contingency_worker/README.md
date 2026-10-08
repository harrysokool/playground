# 2027 Contingent Worker Business Case – GIA HK Data Analytics

Business case requesting approval of **one contingent worker for GIA HK Data Analytics, up to 1,400 hours in 2027**.
The resource supports planned audit engagements and practical AI and automation development within GIA HK,
complementing continued support from TSS and DNA.

**Audience:** CFO and Group Head of Internal Audit.
**Cost:** not included in the deck by design; HR and Finance assess cost separately.

## Folder structure

| Folder | Contents |
|---|---|
| `source/` | Original business case notes (`Business Case for Contingent Worker.pdf`). Do not edit. |
| `template/` | Official AIA PowerPoint template (`aia_ppt_template.pptx`). Do not edit. |
| `current/` | Latest candidate deck: `GIA_HK_2027_Contingent_Worker_Business_Case_v3.pptx` |
| `previews/` | PDF preview of the current deck |
| `archive/v1/`, `archive/v2/` | Earlier versions with their PDF previews (kept unchanged) |
| `scripts/generate_ppt.py` | Generates the current deck from the template |

## Regenerate the deck

Requires Python 3.9+ and `python-pptx` (`pip install python-pptx`). Run from this folder:

```bash
python3 scripts/generate_ppt.py
```

This writes `current/GIA_HK_2027_Contingent_Worker_Business_Case_v3.pptx`. The script never overwrites an existing
file unless `--force` is given, and refuses to write into `archive/`, `source/` or `template/`.
To check reproduction without touching the current file, write elsewhere:

```bash
python3 scripts/generate_ppt.py --output /tmp/check.pptx
```

For a new version, update `DECK_NAME` in the script and move the previous deck to `archive/`.

## Generate the PDF preview

Requires LibreOffice (`soffice` on the PATH; on macOS it is inside `/Applications/LibreOffice.app/Contents/MacOS/`):

```bash
soffice --headless --convert-to pdf --outdir previews current/GIA_HK_2027_Contingent_Worker_Business_Case_v3.pptx
mv previews/GIA_HK_2027_Contingent_Worker_Business_Case_v3.pdf previews/GIA_HK_2027_Contingent_Worker_Business_Case_v3_preview.pdf
```

LibreOffice substitutes some fonts, so the preview is for review only. For a distribution copy, export to PDF from
PowerPoint after applying the sensitivity label.

## Outstanding before distribution

1. **Sensitivity classification.** The deck still carries the template's **[AIA – PUBLIC]** Microsoft sensitivity label.
   The source PDF is labelled *Confidential – Any User*. Apply the label in PowerPoint
   (Home → Sensitivity → *Confidential – Any User*, or the equivalent label name in AIA's list), then save.
   PowerPoint updates both the file label and the footer marking.
2. Confirm the four 2027 engagements are in the final audit plan.
3. Verify the approximate count of 259 regulatory documents (slide 4).
4. Confirm management accepts the proposed accountability measures and the progress review (slide 7).
5. Add presenter name and date, if required.
