/**
 * queryLog.js: Session-scoped query activity store for the Kolko Ni Struva React app.
 * Provides subscription and mutation helpers for recording browser-visible Supabase query intent.
 */

// Keep only the most recent entries so the in-memory session log stays bounded.
const MAX_QUERY_LOG_ENTRIES = 250;

let queryLogEntries = [];
let queryLogSequence = 0;
const queryLogListeners = new Set();

/**
 * Returns the current session query-log snapshot.
 *
 * @returns {Object[]} Immutable snapshot of recorded query entries.
 */
export function getQueryLogSnapshot() {
  return queryLogEntries;
}

/**
 * Subscribes a listener to query-log updates.
 *
 * @param {Function} listener - Callback invoked after the session log changes.
 * @returns {Function} Unsubscribe function for removing the listener.
 */
export function subscribeToQueryLog(listener) {
  queryLogListeners.add(listener);
  return () => {
    queryLogListeners.delete(listener);
  };
}

/**
 * Adds one recorded query entry to the session log.
 *
 * @param {Object} entry - Query entry metadata to append to the current session log.
 * @returns {void}
 */
export function addQueryLogEntry(entry) {
  queryLogSequence += 1;
  queryLogEntries = [
    ...queryLogEntries,
    {
      id: queryLogSequence,
      ...entry,
    },
  ].slice(-MAX_QUERY_LOG_ENTRIES);

  queryLogListeners.forEach((listener) => listener());
}

/**
 * Clears the current in-memory query log.
 *
 * @returns {void}
 */
export function clearQueryLog() {
  queryLogEntries = [];
  queryLogListeners.forEach((listener) => listener());
}

/**
 * Resets query-log state for test isolation.
 *
 * @returns {void}
 */
export function _resetQueryLog() {
  queryLogEntries = [];
  queryLogSequence = 0;
  queryLogListeners.clear();
}