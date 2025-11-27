importScripts('https://www.gstatic.com/firebasejs/9.23.0/firebase-app-compat.js');
importScripts('https://www.gstatic.com/firebasejs/9.23.0/firebase-messaging-compat.js');

firebase.initializeApp({
  apiKey: "AIzaSyDCbscaxKOhdDpHqN4Ahbb7IuwePqGMdq8",
  authDomain: "novafrost-erp-push.firebaseapp.com",
  projectId: "novafrost-erp-push",
  storageBucket: "novafrost-erp-push.firebasestorage.app",
  messagingSenderId: "577173023182",
  appId: "1:577173023182:web:f513e497d43f1a43e6e39f",
  measurementId: "G-LME3H9NE3W"
});

const messaging = firebase.messaging();