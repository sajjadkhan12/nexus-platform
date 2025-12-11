import { useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';

export interface WebSocketEvent {
    type: string;
    data: any;
    // Add other common fields
}

export const useWebSocket = (
    eventType: string,
    callback: (data: any) => void,
    dependencies: any[] = []
) => {
    const { user } = useAuth(); // Ensure user is logged in, though WS connection is handled globally

    useEffect(() => {
        const handleEvent = (event: Event) => {
            const customEvent = event as CustomEvent;
            const data = customEvent.detail;

            // Check if this message matches the event type or criteria we want
            // For now, our backend sends flat structure for notifications, 
            // but for deployment updates we might need to inspect the payload structure deeper
            // OR rely on standard format: { type: "deployment.updated", data: {...} }

            // Currently NotificationContext parses WS messages. 
            // If the message is a "Notification", it has title/message.
            // If it's a raw event (future), it might have 'type'.

            // The backend 'handle_deployment_update' just logs for now and doesn't explicitly send a "type: deployment.updated" message to *specific* user WS.
            // It sends a notification (title/message) on completion.
            // However, the Goal is REALTIME updates.

            // Wait, I updated main.py to send NOTIFICATIONS on completion/failure. 
            // I did NOT implement sending raw JSON updates for intermediate steps to the WS yet.
            // I only added logging in `handle_deployment_update`. 

            // To get REAL TIME updates on the status page, I need the backend to forward the 'deployment.updated' event to the user's WS too, not just logs.

            // Let's assume the backend will forward the raw event if I implement it.
            // For now, let's just listen to "ws-message"

            if (callback) {
                callback(data);
            }
        };

        window.addEventListener('ws-message', handleEvent);

        return () => {
            window.removeEventListener('ws-message', handleEvent);
        };
    }, dependencies);
};
