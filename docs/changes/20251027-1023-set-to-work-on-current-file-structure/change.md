## What

The process of download and refresh of the data to work on the new file structure.

## Why

To continue with regular refreshes and to continue with further enhancements.

## Acceptance Criteria:

- From the scripts /scripts/update.sh and /scripts/build.sh to be created a single refresh.sh script which do all at once - from data download to creation of new deployable in Netlify version. No need to deal with the upload to Netlify now - it will be created later
- The refresh.sh script download the last 3 days and prepare the site with the last 2 days
- The web site should be generated in folder /build/web
- No more references to folder /web-deploy should exist in the code
