# Medlivo Recruit AI: browser preview

**Open the working workspace:**
https://pks-alt.github.io/Medlivo-AI-Platform/workspace-preview/

This is the JobDiva-independent sample workspace supplied on 5 October 2026.
It is separate from the older repository homepage and the Cloud Run application.

The page includes Today, Jobs, Candidates, Customers, Conversations, Submissions,
Follow-ups, Manager and Settings. Sample actions are stored in the current browser.
All clinician, client, job, message and credential records are fictional. Nothing
is sent to JobDiva, an AI provider, email, SMS or a client. The demo persona selector
is not a production login or a security boundary. Enter sample information only.

## Try the sample approval workflow

With Alex Chen selected, open Jobs, then Physical Therapist in Dallas and Jamie
Sullivan. Complete References reviewed, mark the sample ready for review, and
approve the sample packet. Packet previews are clearly labeled NOT SUBMITTED.

## Build integrity

`index.html` is the exact standalone artifact, with its original Content Security
Policy hashes preserved. Its SHA-256 is:

```
87c73df07dfc320c0e38c1075b153cc715289b49df4afeb6f3b298e8d98d0c48
```

The five `build-part-*.txt` files are a base64-encoded gzip transfer of this artifact.
They are not runtime dependencies. The publication workflow checks their decoded
checksum before creating the page and refuses to overwrite a different preview.

The Publish and verify sample workspace workflow checks hosted bytes, browser
navigation, sample approval, browser storage and mobile layout. Consult its latest
completed result for verification status; source publication alone does not prove
a successful browser test.
