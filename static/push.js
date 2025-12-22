import { initializeApp } from "https://www.gstatic.com/firebasejs/9.23.0/firebase-app.js";
import { getMessaging, getToken, onMessage } from "https://www.gstatic.com/firebasejs/9.23.0/firebase-messaging.js";

const firebaseConfig = {
  apiKey: "AIzaSyDCbscaxKOhdDpHqN4Ahbb7IuwePqGMdq8",
  authDomain: "novafrost-erp-push.firebaseapp.com",
  projectId: "novafrost-erp-push",
  storageBucket: "novafrost-erp-push.firebasestorage.app",
  messagingSenderId: "577173023182",
  appId: "1:577173023182:web:f513e497d43f1a43e6e39f",
  measurementId: "G-LME3H9NE3W"
};

const app = initializeApp(firebaseConfig);

const messaging = getMessaging();

async function registrarToken() {
    try {
        const token = await getToken(messaging, { vapidKey: "BH9k... (te lo doy en 2 segundos)" });
        if (token) {
            // Enviamos el token al backend
            await fetch('/guardar_token_push', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ token: token })
            });
            console.log("Token registrado:", token);
        }
    } catch (err) {
        console.log("Error al obtener token:", err);
    }
}

// Pedir permiso cuando el técnico entra al dashboard
if (Notification.permission === "default") {
    Notification.requestPermission().then(perm => {
        if (perm === "granted") registrarToken();
    });
} else if (Notification.permission === "granted") {
    registrarToken();
}
