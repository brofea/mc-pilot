package mc.pilot.mod;

/**
 * Central command routing logic.
 */
public class PilotCommandHandler {

    private PilotCommandHandler() {}

    public static String route(PilotClient client, String message) {
        if (message == null || message.isBlank()) {
            return getHelpText();
        }

        String text = message.trim();
        String lower = text.toLowerCase();

        if (lower.equals("/pilot status") || lower.equals("status")) {
            return "Pilot Mod v0.1.0\n"
                    + "HTTP: " + (client.isHttpReachable() ? "connected" : "disconnected") + "\n"
                    + "WebSocket: " + (PilotClient.isWebSocketConnected() ? "connected" : "disconnected");
        }

        if (lower.equals("/pilot clear") || lower.equals("clear")) {
            client.clearSession();
            return "Session cleared.";
        }

        if (lower.equals("/pilot help") || lower.equals("help")) {
            return getHelpText();
        }

        // All other queries go to agent
        return null; // signal to send to backend
    }

    private static String getHelpText() {
        return "Pilot Agent:\n"
                + "  /pilot <query>  - Ask the agent\n"
                + "  /pilot wiki <term> - Search wiki\n"
                + "  /pilot recipe <id> - Query recipe\n"
                + "  /pilot status - Connection status\n"
                + "  /pilot clear - Clear memory\n"
                + "  /pilot help - This help";
    }
}
