package mc.pilot.mod;

import com.mojang.brigadier.arguments.StringArgumentType;
import net.fabricmc.api.ClientModInitializer;
import net.fabricmc.fabric.api.client.command.v2.ClientCommands;
import net.fabricmc.fabric.api.client.command.v2.ClientCommandRegistrationCallback;
import net.fabricmc.fabric.api.client.event.lifecycle.v1.ClientTickEvents;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class PilotMod implements ClientModInitializer {

    public static final String MOD_ID = "pilot-mod";
    public static final Logger LOGGER = LoggerFactory.getLogger(MOD_ID);

    private static final String BACKEND_HOST = "127.0.0.1";
    private static final int BACKEND_HTTP_PORT = 8000;

    private static PilotClient client;
    private static int reconnectTicks;
    private static boolean backendWasDown;

    @Override
    public void onInitializeClient() {
        LOGGER.info("Minecraft Pilot Mod initializing");

        client = new PilotClient(BACKEND_HOST, BACKEND_HTTP_PORT);
        reconnectTicks = 0;
        backendWasDown = false;

        ClientCommandRegistrationCallback.EVENT.register((dispatcher, registryAccess) -> {
            dispatcher.register(
                ClientCommands.literal("pilot")
                    .executes(ctx -> {
                        ChatRenderer.addLocalMessage(
                            PilotCommandHandler.route(client, "")
                        );
                        return 1;
                    })
                    .then(
                        ClientCommands.argument("text", StringArgumentType.greedyString())
                            .executes(ctx -> {
                                String text = StringArgumentType.getString(ctx, "text");
                                String local = PilotCommandHandler.route(client, "/pilot " + text);
                                if (local != null) {
                                    ChatRenderer.addLocalMessage(local);
                                } else {
                                    client.sendQuery("/pilot " + text);
                                }
                                return 1;
                            })
                    )
            );
        });

        ClientTickEvents.END_CLIENT_TICK.register(tickClient -> {
            reconnectTicks++;
            if (reconnectTicks % 200 == 0) {
                client.connectWebSocket();
                if (!PilotClient.isWebSocketConnected() && !backendWasDown) {
                    backendWasDown = true;
                    ChatRenderer.addLocalMessage("Pilot backend disconnected.");
                } else if (PilotClient.isWebSocketConnected() && backendWasDown) {
                    backendWasDown = false;
                    ChatRenderer.addLocalMessage("Pilot backend reconnected.");
                }
            }
            client.pollMessages();
        });

        LOGGER.info("Minecraft Pilot Mod initialized");
    }

    public static PilotClient getClient() {
        return client;
    }
}
