// Firebase Auth wiring for the browser client. Loaded straight from
// Google's CDN as ES modules - no bundler needed, matching the rest of
// web/'s no-build-step approach. The browser talks to Firebase Auth
// directly (the standard pattern - see project-rampart-browser-port memory
// note); everything else (game data, usernames) only ever goes through
// server/, which verifies the ID token this file hands out.

import { initializeApp } from 'https://www.gstatic.com/firebasejs/12.18.0/firebase-app.js';
import {
    getAuth, createUserWithEmailAndPassword, signInWithEmailAndPassword,
    onAuthStateChanged, signOut, sendEmailVerification, sendPasswordResetEmail,
} from 'https://www.gstatic.com/firebasejs/12.18.0/firebase-auth.js';
import {
    getStorage, ref as storageRef, uploadBytes, getDownloadURL,
} from 'https://www.gstatic.com/firebasejs/12.18.0/firebase-storage.js';

// Public web app config for the rampart-bea61 project (the same one
// io_src_dev's pyrebase client already uses) - safe to embed client-side by
// Firebase's own design; access is controlled by Firebase Auth + the
// server's own token verification, not by keeping this secret.
const firebaseConfig = {
    apiKey: 'AIzaSyC9k3NRCA4VhzPOof8fcpVGYdSZ582vsKo',
    authDomain: 'rampart-bea61.firebaseapp.com',
    databaseURL: 'https://rampart-bea61-default-rtdb.firebaseio.com',
    projectId: 'rampart-bea61',
    storageBucket: 'rampart-bea61.firebasestorage.app',
    messagingSenderId: '69040292066',
    appId: '1:69040292066:web:3ad41d9e4ff57bfe7a9ebb',
};

const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);

export function signUpWithEmail(email, password) {
    return createUserWithEmailAndPassword(auth, email, password);
}

export function logInWithEmail(email, password) {
    return signInWithEmailAndPassword(auth, email, password);
}

export function logOut() {
    return signOut(auth);
}

// Soft nudge, not a gate - nothing in server/ checks email_verified, so
// this only ever drives a UI reminder (see the banner in main.js). Firebase
// itself has no way to check verification status for anyone but the
// currently signed-in user, which is all a soft nudge needs anyway.
export function sendVerificationEmail() {
    return auth.currentUser ? sendEmailVerification(auth.currentUser) : Promise.resolve();
}

export function isEmailVerified() {
    return Boolean(auth.currentUser && auth.currentUser.emailVerified);
}

export function resetPassword(email) {
    return sendPasswordResetEmail(auth, email);
}

export function onAuthChange(callback) {
    return onAuthStateChanged(auth, callback);
}

export function getIdToken() {
    return auth.currentUser ? auth.currentUser.getIdToken() : Promise.resolve(null);
}

// Avatars are stored at a fixed path per uid (avatars/{uid}, secured by
// Storage rules restricting writes to that uid's own owner and public
// read - see the rules pasted into the console) rather than tracked in the
// Realtime Database at all, so there's no second source of truth to keep
// in sync: the image either exists at that path or it doesn't.
export const storage = getStorage(app);

export async function uploadAvatar(uid, blob) {
    const avatarRef = storageRef(storage, `avatars/${uid}`);
    await uploadBytes(avatarRef, blob, { contentType: 'image/jpeg' });
    return getDownloadURL(avatarRef);
}

// Resolves to the avatar's download URL, or null if none has been
// uploaded (Storage 404s - not an error, just "no custom avatar yet").
export async function getAvatarUrl(uid) {
    try {
        return await getDownloadURL(storageRef(storage, `avatars/${uid}`));
    } catch (e) {
        return null;
    }
}
