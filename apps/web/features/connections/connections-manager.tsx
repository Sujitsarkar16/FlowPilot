"use client";

import { type FormEvent, type RefObject, useCallback, useEffect, useRef, useState } from "react";

import { ConfirmDialog } from "@/components/confirm-dialog";
import { ErrorState } from "@/components/error-state";
import { LoadingSkeleton } from "@/components/loading-skeleton";
import { StatusBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api/client";
import type { Connection, ConnectionProvider } from "@/lib/api/types";

const connectors = [
  {
    provider: "google",
    name: "Google",
    description: "Bring Gmail, Calendar, and Drive context into your workspace.",
    permissions: ["Read Gmail messages", "Manage Calendar events", "Read Drive files"],
  },
  {
    provider: "github",
    name: "GitHub",
    description: "Connect repositories so relevant project activity can be understood.",
    permissions: ["Access public repositories"],
  },
  {
    provider: "telegram",
    name: "Telegram",
    description: "Send notifications to a chat that you choose.",
    permissions: ["Send messages to the specified chat"],
  },
] as const;

type OAuthProvider = Extract<ConnectionProvider, "google" | "github">;

function connectionFor(connections: Connection[], provider: ConnectionProvider) {
  return connections.find((connection) => connection.provider === provider);
}

export function ConnectionsManager() {
  const [connections, setConnections] = useState<Connection[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<unknown>(null);
  const [actionError, setActionError] = useState<unknown>(null);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [disconnectTarget, setDisconnectTarget] = useState<Connection | null>(null);
  const [telegramOpen, setTelegramOpen] = useState(false);
  const [telegramToken, setTelegramToken] = useState("");
  const [telegramChatId, setTelegramChatId] = useState("");
  const [telegramError, setTelegramError] = useState<string | null>(null);
  const telegramTokenRef = useRef<HTMLInputElement>(null);

  const loadConnections = useCallback(async () => {
    setLoading(true);
    setLoadError(null);
    try {
      setConnections(await api.listConnections());
    } catch (error) {
      setLoadError(error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadConnections();
  }, [loadConnections]);

  useEffect(() => {
    if (!telegramOpen) return;
    telegramTokenRef.current?.focus();
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape" && !busy) setTelegramOpen(false);
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [busy, telegramOpen]);

  const startOAuth = async (provider: OAuthProvider) => {
    setBusy(`oauth-${provider}`);
    setActionError(null);
    setFeedback(null);
    try {
      const { authorization_url } = await api.startOAuth(provider);
      setFeedback(`Redirecting you to ${provider === "google" ? "Google" : "GitHub"}.`);
      window.location.assign(authorization_url);
    } catch (error) {
      setActionError(error);
    } finally {
      setBusy(null);
    }
  };

  const testConnection = async (connection: Connection) => {
    setBusy(`test-${connection.id}`);
    setActionError(null);
    setFeedback(null);
    try {
      await api.testConnection(connection.id);
      await loadConnections();
      setFeedback(`${connection.provider === "github" ? "GitHub" : connection.provider === "google" ? "Google" : "Telegram"} connection test passed.`);
    } catch (error) {
      setActionError(error);
    } finally {
      setBusy(null);
    }
  };

  const disconnect = async () => {
    if (!disconnectTarget) return;
    setBusy(`disconnect-${disconnectTarget.id}`);
    setActionError(null);
    try {
      await api.disconnect(disconnectTarget.id);
      await loadConnections();
      setFeedback("Connection disconnected.");
      setDisconnectTarget(null);
    } catch (error) {
      setActionError(error);
    } finally {
      setBusy(null);
    }
  };

  const submitTelegram = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!telegramToken.trim() || !telegramChatId.trim()) {
      setTelegramError("Enter both the bot token and destination chat ID.");
      return;
    }
    setBusy("telegram");
    setActionError(null);
    setTelegramError(null);
    try {
      await api.setupTelegram({ bot_token: telegramToken, chat_id: telegramChatId });
      setTelegramToken("");
      setTelegramChatId("");
      await loadConnections();
      setTelegramOpen(false);
      setFeedback("Telegram connection saved.");
    } catch (error) {
      setActionError(error);
    } finally {
      setBusy(null);
    }
  };

  const openTelegram = () => {
    setTelegramError(null);
    setActionError(null);
    setTelegramOpen(true);
  };

  return (
    <div className="mx-auto max-w-7xl p-4 pb-24 sm:p-6 md:pb-8">
      <div className="mb-6 max-w-3xl">
        <h1 className="text-2xl font-semibold tracking-tight text-slate-950 sm:text-3xl">
          Connections
        </h1>
        <p className="mt-2 text-sm leading-6 text-slate-600">
          Choose the services PulseOS can use. Review the requested permissions before you connect.
          Credentials stay encrypted and are never shown here.
        </p>
      </div>

      {actionError ? <ErrorState className="mb-4" error={actionError} title="Action failed" /> : null}
      {feedback ? (
        <p aria-live="polite" className="mb-4 text-sm font-medium text-emerald-800" role="status">
          {feedback}
        </p>
      ) : null}

      {loading ? (
        <LoadingSkeleton className="h-80" label="Loading connections" />
      ) : loadError ? (
        <div className="space-y-4">
          <ErrorState error={loadError} />
          <Button onClick={() => void loadConnections()} type="button" variant="outline">
            Try again
          </Button>
        </div>
      ) : (
        <section aria-label="Available connections" className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          {connectors.map((connector) => {
            const connection = connectionFor(connections, connector.provider);
            const connected = connection?.status === "connected";
            const oauth = connector.provider !== "telegram";
            const providerName = connector.name;
            return (
              <Card className="flex min-h-80 flex-col" key={connector.provider}>
                <CardHeader className="gap-3">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <CardTitle>{connector.name}</CardTitle>
                      <p className="mt-2 text-sm leading-5 text-slate-600">{connector.description}</p>
                    </div>
                    <StatusBadge status={connection?.status ?? "not connected"} />
                  </div>
                  {connection ? (
                    <p className="text-xs text-slate-500">
                      Connected account: {connection.provider_account_id}
                    </p>
                  ) : null}
                </CardHeader>
                <CardContent className="flex flex-1 flex-col">
                  <section aria-label={`${connector.name} permission disclosure`}>
                    <h3 className="text-sm font-medium text-slate-900">Requested permissions</h3>
                    <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-600">
                      {connector.permissions.map((permission) => (
                        <li key={permission}>{permission}</li>
                      ))}
                    </ul>
                  </section>
                  {connection?.scopes.length ? (
                    <p className="mt-4 text-xs text-slate-500">
                      Granted: {connection.scopes.join(", ")}
                    </p>
                  ) : null}
                  <div className="mt-auto flex flex-wrap gap-2 pt-6">
                    {oauth ? (
                      <Button
                        disabled={busy !== null}
                        onClick={() => void startOAuth(connector.provider)}
                        type="button"
                      >
                        {connection ? "Reconnect" : `Connect ${providerName}`}
                      </Button>
                    ) : (
                      <Button disabled={busy !== null} onClick={openTelegram} type="button">
                        {connection ? "Update setup" : "Connect Telegram"}
                      </Button>
                    )}
                    {connected ? (
                      <Button
                        disabled={busy !== null}
                        onClick={() => void testConnection(connection)}
                        type="button"
                        variant="outline"
                      >
                        {busy === `test-${connection.id}` ? "Testing…" : "Test"}
                      </Button>
                    ) : null}
                    {connection ? (
                      <Button
                        className="text-red-700 hover:bg-red-50 hover:text-red-800"
                        disabled={busy !== null}
                        onClick={() => {
                          setActionError(null);
                          setDisconnectTarget(connection);
                        }}
                        type="button"
                        variant="ghost"
                      >
                        Disconnect
                      </Button>
                    ) : null}
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </section>
      )}

      <TelegramDialog
        busy={busy === "telegram"}
        chatId={telegramChatId}
        error={telegramError}
        onCancel={() => setTelegramOpen(false)}
        onChatIdChange={setTelegramChatId}
        onSubmit={submitTelegram}
        onTokenChange={setTelegramToken}
        open={telegramOpen}
        token={telegramToken}
        tokenRef={telegramTokenRef}
      />
      <ConfirmDialog
        busy={busy === `disconnect-${disconnectTarget?.id}`}
        confirmLabel="Disconnect"
        description={`This will revoke PulseOS access to ${disconnectTarget?.provider_account_id ?? "this account"}. You can reconnect later.`}
        destructive
        onCancel={() => setDisconnectTarget(null)}
        onConfirm={() => void disconnect()}
        open={disconnectTarget !== null}
        title="Disconnect this connection?"
      />
    </div>
  );
}

function TelegramDialog({
  busy,
  chatId,
  error,
  onCancel,
  onChatIdChange,
  onSubmit,
  onTokenChange,
  open,
  token,
  tokenRef,
}: {
  busy: boolean;
  chatId: string;
  error: string | null;
  onCancel: () => void;
  onChatIdChange: (chatId: string) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onTokenChange: (token: string) => void;
  open: boolean;
  token: string;
  tokenRef: RefObject<HTMLInputElement | null>;
}) {
  if (!open) return null;
  return (
    <div
      aria-describedby="telegram-setup-description"
      aria-labelledby="telegram-setup-title"
      aria-modal="true"
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/50 p-4"
      role="dialog"
    >
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle id="telegram-setup-title">Connect Telegram</CardTitle>
          <p className="text-sm text-slate-600" id="telegram-setup-description">
            Your bot token is sent only to set up this connection and is never displayed or stored in
            the browser.
          </p>
        </CardHeader>
        <CardContent>
          <form className="space-y-4" onSubmit={onSubmit}>
            <div>
              <label className="text-sm font-medium text-slate-900" htmlFor="telegram-bot-token">
                Bot token
              </label>
              <input
                autoComplete="off"
                className="mt-1 block w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-950 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                disabled={busy}
                id="telegram-bot-token"
                onChange={(event) => onTokenChange(event.target.value)}
                ref={tokenRef}
                required
                type="password"
                value={token}
              />
            </div>
            <div>
              <label className="text-sm font-medium text-slate-900" htmlFor="telegram-chat-id">
                Destination chat ID
              </label>
              <input
                autoComplete="off"
                className="mt-1 block w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-950 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                disabled={busy}
                id="telegram-chat-id"
                onChange={(event) => onChatIdChange(event.target.value)}
                required
                type="text"
                value={chatId}
              />
            </div>
            {error ? <p className="text-sm text-red-700" role="alert">{error}</p> : null}
            <div className="flex justify-end gap-3">
              <Button disabled={busy} onClick={onCancel} type="button" variant="outline">
                Cancel
              </Button>
              <Button disabled={busy} type="submit">
                {busy ? "Saving…" : "Save connection"}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
