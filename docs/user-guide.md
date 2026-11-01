# User guide

This page explains how to use the app and what to expect. The
[installation guide](installation.md) explains how to start it.

Replace the text below with the real behaviour of the project.

## Searching

1. Open the app in a browser.
2. Type a word into the box.
3. Press **Search**.

The page then shows `You searched for:` followed by your word. Spaces at
either end are removed.

## Messages

- `Error: No input provided`: the box was empty or held only spaces. Type
  something and search again.
- `Error: Something went wrong. Please try again.`: the app hit an error it
  did not expect. The details, with the full traceback, are in the log file
  (see [Logging](logging.md)).
