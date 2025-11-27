import { getMessaging, getToken, onMessage } from "https://www.gstatic.com/firebasejs/9.23.0/firebase-messaging.js";

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