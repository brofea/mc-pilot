package mc.pilot.mod;

import net.minecraft.client.MinecraftClient;
import net.minecraft.text.Text;

public class ChatRenderer {

    private static final String PREFIX = "[Pilot] ";

    public static void addLocalMessage(String message) {
        MinecraftClient client = MinecraftClient.getInstance();
        if (client == null || client.player == null) return;

        // Split long messages into reasonable chunks for chat HUD
        if (message.length() > 200) {
            for (int i = 0; i < message.length(); i += 180) {
                String chunk = PREFIX + message.substring(i, Math.min(i + 180, message.length()));
                sendToChat(client, Text.literal(chunk));
            }
        } else {
            sendToChat(client, Text.literal(PREFIX + message));
        }
    }

    private static void sendToChat(MinecraftClient client, Text text) {
        client.execute(() -> {
            if (client.player != null) {
                client.player.sendMessage(text, false);
            }
        });
    }
}
