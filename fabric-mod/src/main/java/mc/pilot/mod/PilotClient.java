package mc.pilot.mod;

import com.google.gson.Gson;
import com.google.gson.JsonObject;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.net.http.WebSocket;
import java.time.Duration;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.CompletionStage;
import java.util.concurrent.ConcurrentLinkedQueue;

public class PilotClient {

    private static final Logger LOGGER = LoggerFactory.getLogger(PilotClient.class);
    private static final Gson GSON = new Gson();

    private final String httpBase;
    private final String wsUrl;
    private final HttpClient httpClient;
    private final ConcurrentLinkedQueue<String> incomingMessages;

    private static WebSocket webSocket;
    private static boolean webSocketConnected;
    private String sessionId;

    public PilotClient(String host, int httpPort) {
        this.httpBase = "http://" + host + ":" + httpPort;
        this.wsUrl = "ws://" + host + ":" + httpPort + "/ws";
        this.httpClient = HttpClient.newBuilder()
                .connectTimeout(Duration.ofSeconds(5))
                .build();
        this.incomingMessages = new ConcurrentLinkedQueue<>();
        this.sessionId = "mod-" + System.currentTimeMillis();
        connectWebSocket();
    }

    public void connectWebSocket() {
        if (webSocketConnected) return;

        try {
            CompletableFuture<WebSocket> future = httpClient.newWebSocketBuilder()
                    .connectTimeout(Duration.ofSeconds(3))
                    .buildAsync(URI.create(wsUrl), new PilotWebSocketListener());

            future.thenAccept(ws -> {
                webSocket = ws;
                webSocketConnected = true;
                LOGGER.info("WebSocket connected to {}", wsUrl);
            }).exceptionally(ex -> {
                webSocketConnected = false;
                LOGGER.debug("WebSocket connection failed: {}", ex.getMessage());
                return null;
            });
        } catch (Exception e) {
            webSocketConnected = false;
        }
    }

    public static boolean isWebSocketConnected() {
        return webSocketConnected && webSocket != null && !webSocket.isOutputClosed();
    }

    public boolean isHttpReachable() {
        try {
            HttpRequest req = HttpRequest.newBuilder()
                    .uri(URI.create(httpBase + "/health/live"))
                    .timeout(Duration.ofSeconds(2))
                    .GET()
                    .build();
            HttpResponse<String> resp = httpClient.send(req, HttpResponse.BodyHandlers.ofString());
            return resp.statusCode() == 200;
        } catch (Exception e) {
            return false;
        }
    }

    public void sendQuery(String message) {
        CompletableFuture.runAsync(() -> {
            try {
                JsonObject body = new JsonObject();
                body.addProperty("message", message);
                body.addProperty("session_id", sessionId);

                HttpRequest req = HttpRequest.newBuilder()
                        .uri(URI.create(httpBase + "/api/chat"))
                        .timeout(Duration.ofSeconds(30))
                        .header("Content-Type", "application/json")
                        .POST(HttpRequest.BodyPublishers.ofString(GSON.toJson(body)))
                        .build();

                HttpResponse<String> resp = httpClient.send(req, HttpResponse.BodyHandlers.ofString());

                if (resp.statusCode() == 200) {
                    JsonObject result = GSON.fromJson(resp.body(), JsonObject.class);
                    String answer = result.has("answer")
                            ? result.get("answer").getAsString()
                            : "(无回复)";
                    ChatRenderer.addLocalMessage(answer);

                    if (result.has("stop_reason") && !result.get("stop_reason").isJsonNull()) {
                        ChatRenderer.addLocalMessage("[提示: " + result.get("stop_reason").getAsString() + "]");
                    }
                } else {
                    ChatRenderer.addLocalMessage("Pilot 后端错误: HTTP " + resp.statusCode());
                }
            } catch (Exception e) {
                ChatRenderer.addLocalMessage("无法连接 Pilot 后端。请确认后端已启动。");
                LOGGER.error("Query failed", e);
            }
        });
    }

    public void clearSession() {
        this.sessionId = "mod-" + System.currentTimeMillis();
    }

    public void pollMessages() {
        String msg;
        while ((msg = incomingMessages.poll()) != null) {
            ChatRenderer.addLocalMessage(msg);
        }
    }

    private class PilotWebSocketListener implements WebSocket.Listener {

        private final StringBuilder buffer = new StringBuilder();

        @Override
        public void onOpen(WebSocket webSocket) {
            LOGGER.info("WebSocket opened");
            WebSocket.Listener.super.onOpen(webSocket);
        }

        @Override
        public CompletionStage<?> onText(WebSocket webSocket, CharSequence data, boolean last) {
            buffer.append(data);
            if (last) {
                String message = buffer.toString();
                buffer.setLength(0);
                try {
                    JsonObject json = GSON.fromJson(message, JsonObject.class);
                    String type = json.has("type") ? json.get("type").getAsString() : "";
                    if ("death_advice".equals(type)) {
                        String advice = json.has("advice") ? json.get("advice").getAsString() : "";
                        String player = json.has("player_name") ? json.get("player_name").getAsString() : "";
                        String category = json.has("category") ? json.get("category").getAsString() : "";
                        incomingMessages.add("[" + player + " 死亡 - " + category + "] " + advice);
                    }
                } catch (Exception e) {
                    incomingMessages.add("[Pilot] " + message);
                }
            }
            webSocket.request(1);
            return null;
        }

        @Override
        public void onError(WebSocket webSocket, Throwable error) {
            LOGGER.warn("WebSocket error: {}", error.getMessage());
            webSocketConnected = false;
        }

        @Override
        public CompletionStage<?> onClose(WebSocket webSocket, int statusCode, String reason) {
            LOGGER.info("WebSocket closed: {} {}", statusCode, reason);
            webSocketConnected = false;
            return null;
        }
    }
}
