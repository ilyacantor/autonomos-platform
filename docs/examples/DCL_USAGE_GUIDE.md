# DCL Bridge - Usage Guide

**Last Updated:** November 19, 2025

## Overview

The **DCL Bridge** adds Legacy DCL functionality to the Modern authenticated UI without requiring frontend rebuilds. It injects JavaScript that connects the Modern UI to Legacy DCL endpoints.

## How It Works

```
┌─────────────────────┐
│   Modern UI (React) │  ← User logs in
│   + DCL Bridge JS   │  ← DCL Bridge injected
└──────────┬──────────┘
           │
           ├─→ /api/v1/auth/*     → Modern Auth API
           ├─→ /api/v1/aoa/*      → Modern AOA API  
           │
           ├─→ /connect           → Legacy DCL endpoints
           ├─→ /reset             │  (proxy to /dcl/*)
           ├─→ /toggle_dev_mode   │
           └─→ /state             ┘
                     │
                     ↓
           ┌──────────────────┐
           │  DCL Engine      │
           │  (Embedded)      │
           └──────────────────┘
```

## Usage Methods

### Method 1: Browser Console (Recommended)

Open browser console (F12) and use the exposed window functions:

```javascript
// Connect all 9 data sources to both agents
window.dclConnect(
  'dynamics,salesforce,hubspot,sap,netsuite,legacy_sql,snowflake,supabase,mongodb',
  'revops_pilot,finops_pilot'
);

// Reset demo state
window.dclReset();

// Toggle dev mode (AI vs Heuristic mapping)
window.dclToggleDevMode();
```

### Method 2: Keyboard Shortcuts

- **Ctrl+Shift+D** - Connect default sources (dynamics, salesforce, hubspot)
- **Ctrl+Shift+R** - Reset DCL demo
- **Ctrl+Shift+M** - Toggle dev mode

### Method 3: Existing UI Buttons

Any button containing "Run" text is automatically enhanced to trigger DCL connect when clicked.

## DCL State Monitoring

The DCL Bridge automatically polls `/state` every 3 seconds and logs the current state to the console:

```javascript
[DCL State] {
  sources: ["dynamics", "salesforce", "hubspot"],
  agents: ["revops_pilot", "finops_pilot"],
  devMode: false
}
```

## Available Endpoints

| Endpoint | Method | Purpose | Example |
|----------|--------|---------|---------|
| `/state` | GET | Get DCL state | `curl http://localhost:5000/state` |
| `/connect` | GET | Connect sources | `curl http://localhost:5000/connect?sources=dynamics&agents=revops_pilot` |
| `/reset` | GET | Reset demo | `curl http://localhost:5000/reset` |
| `/toggle_dev_mode` | GET | Toggle AI mode | `curl http://localhost:5000/toggle_dev_mode` |

## Examples

### Example 1: Connect a Single Source

```javascript
window.dclConnect('dynamics', 'revops_pilot');
```

### Example 2: Connect Multiple Sources

```javascript
window.dclConnect(
  'dynamics,salesforce,hubspot',
  'revops_pilot,finops_pilot'
);
```

### Example 3: Reset and Reconnect

```javascript
// Reset the demo
window.dclReset();

// Wait a moment, then connect
setTimeout(() => {
  window.dclConnect('dynamics,salesforce', 'revops_pilot');
}, 1000);
```

### Example 4: Toggle Dev Mode

```javascript
// Toggle to AI/RAG mapping mode
window.dclToggleDevMode();

// Connect sources (will use AI mapping if dev mode is enabled)
window.dclConnect('dynamics', 'revops_pilot');
```

## Console Logging

The DCL Bridge logs all activities to the browser console:

- `[DCL Bridge] Initializing...` - Bridge script loaded
- `[DCL Bridge] Ready!` - Bridge initialized and ready
- `[DCL State]` - Current DCL state (polled every 3 seconds)
- `[DCL] Connecting sources...` - Connection initiated
- `[DCL Connect Success]` - Connection successful
- `[DCL Reset Success]` - Reset successful

## Testing DCL Functionality

1. **Login to the Modern UI** with credentials
2. **Open browser console** (F12)
3. **Wait for DCL Bridge to initialize** - Look for `[DCL Bridge] Ready!`
4. **Run a test connection**:
   ```javascript
   window.dclConnect('dynamics', 'revops_pilot');
   ```
5. **Check the console** for success messages
6. **Verify backend logs** - DCL should show "I connected to Dynamics..."

## Architecture Files

- `static/dcl-bridge.js` - DCL Bridge script (4.3 KB)
- `static/index.html` - Modified to load DCL Bridge
- `app/main.py` - Serves `/dcl-bridge.js` and legacy endpoints
- `app/dcl_engine/app.py` - DCL Engine implementation

## Benefits

✅ **No Frontend Rebuild** - Injected via script tag, no React rebuild required  
✅ **Modern Auth Preserved** - Login/register functionality untouched  
✅ **Console Access** - Full DCL control from browser console  
✅ **Keyboard Shortcuts** - Quick access to DCL functions  
✅ **Auto-Polling** - Real-time DCL state updates  
✅ **Button Enhancement** - Existing "Run" buttons trigger DCL  

## Troubleshooting

### DCL Bridge not loading

Check browser console for script errors. Ensure `/dcl-bridge.js` is accessible:

```bash
curl http://localhost:5000/dcl-bridge.js
```

### Functions not available

Ensure the DCL Bridge has initialized. Look for:

```
[DCL Bridge] Ready!
```

### Endpoints returning 503

Check that the DCL engine is mounted:

```bash
curl http://localhost:5000/dcl/state
```

### No state updates

The DCL Bridge polls every 3 seconds. Check console for:

```
[DCL State] {...}
```

If missing, the fetch may be failing - check network tab.
