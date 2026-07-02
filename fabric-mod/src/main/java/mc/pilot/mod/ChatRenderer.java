package mc.pilot.mod;

import net.minecraft.client.Minecraft;
import net.minecraft.network.chat.Component;

public class ChatRenderer {

    private static final String PREFIX = "[Pilot] ";

    public static void addLocalMessage(String message) {
        Minecraft client = Minecraft.getInstance();
        if (client == null || client.player == null) return;

        // Split long messages into reasonable chunks for chat HUD
        if (message.length() > 200) {
            for (int i = 0; i < message.length(); i += 180) {
                String chunk = PREFIX + message.substring(i, Math.min(i + 180, message.length()));
                sendToChat(client, Component.literal(chunk));
            }
        } else {
            sendToChat(client, Component.literal(PREFIX + message));
        }
    }

    private static void sendToChat(Minecraft client, Component text) {
        client.execute(() -> {
            if (client.player != null) {
                client.gui.hud.getChat().addClientSystemMessage(text);
            }
        });
    }
}
