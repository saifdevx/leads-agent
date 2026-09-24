# Firebase Setup

This application uses Firebase Authentication in the browser and Firebase Admin only on the FastAPI server.

## A. Create or choose a Firebase project

1. Open Firebase Console.
2. Create a project, or select the project you want to use for Lead Gen.
3. You do not need Firestore, Realtime Database, or Firebase Storage for this application.

## B. Enable authentication methods

1. Open **Authentication**.
2. Choose **Get started** if Authentication is not initialized yet.
3. Open **Sign-in method**.
4. Enable **Email/Password**.
5. Enable **Google**.
6. For Google, select the project support email and save.

Do not enable phone/SMS authentication for this application.

## C. Create the Firebase Web App

1. Open **Project settings** (gear icon).
2. Under **General**, find **Your apps**.
3. Add a **Web app** if one does not exist.
4. Give it a name such as `Lead Gen Web`.
5. Firebase will show a configuration object similar to:

```js
const firebaseConfig = {
  apiKey: "...",
  authDomain: "...",
  projectId: "...",
  storageBucket: "...",
  messagingSenderId: "...",
  appId: "..."
}
```

Copy those values into `frontend/.env`:

```env
VITE_API_URL=http://localhost:8000
VITE_FIREBASE_API_KEY=...
VITE_FIREBASE_AUTH_DOMAIN=...
VITE_FIREBASE_PROJECT_ID=...
VITE_FIREBASE_APP_ID=...
VITE_FIREBASE_MESSAGING_SENDER_ID=...
VITE_FIREBASE_STORAGE_BUCKET=...
```

These web-app identifiers are used by the browser. **Do not put a Firebase Admin private key here.**

After editing `frontend/.env`, restart Vite.

## D. Create backend Firebase Admin credentials

1. In Firebase **Project settings**, open **Service accounts**.
2. Choose **Generate new private key**.
3. Confirm the download.
4. Move the downloaded JSON file somewhere outside the Git repository.

Recommended local layout:

```text
D:\Leads-Agent\secrets\lead-gen-firebase-admin.json
D:\Leads-Agent\leads-agent\   <-- Git repository
```

Do not place the key inside `frontend/`, `backend/`, or any committed project folder.

Update `backend/.env`:

```env
APP_NAME=Lead Gen API
APP_VERSION=<use the value from backend/.env.example>
APP_ENV=development
CORS_ORIGINS=http://localhost:5173
LOG_LEVEL=INFO

FIREBASE_PROJECT_ID=your-firebase-project-id
FIREBASE_CREDENTIALS_PATH=D:/Leads-Agent/secrets/lead-gen-firebase-admin.json
FIREBASE_SERVICE_ACCOUNT_JSON=
```

Forward slashes in the Windows path avoid escaping problems.

Restart Uvicorn after changing `backend/.env`.

## E. Local authorized domain

Firebase Authentication normally needs the site domain to be authorized. If Google sign-in reports an unauthorized-domain error:

1. Open Firebase Authentication settings.
2. Find **Authorized domains**.
3. Add `localhost` for local development if it is not already present.

When deploying to Render later, also add the final Render frontend hostname.

## F. Validate the setup

Start backend:

```powershell
cd D:\Leads-Agent\leads-agent\backend
.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000
```

Start frontend:

```powershell
cd D:\Leads-Agent\leads-agent\frontend
npm run dev
```

Open `http://localhost:5173` and register a test user.

If frontend Firebase is configured but backend Firebase Admin is not, you should see a clear **backend authentication verification** error instead of being allowed into the application. This is expected security behavior.

## G. Production/Render note

For Render, do not upload the service-account JSON into the repository.

The application supports `FIREBASE_SERVICE_ACCOUNT_JSON` specifically so the entire service-account JSON can be stored as a secret environment variable on the backend service. `FIREBASE_CREDENTIALS_PATH` is mainly intended for local development or environments with a secure mounted secret file.

The frontend Render service needs the `VITE_FIREBASE_*` values during its build because Vite injects them into the built frontend bundle.

This section only covers authentication configuration; deployment uses the same authentication architecture.
