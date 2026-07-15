# Frontend architecture — M1

## Scope

M1 provides a static Life Feed shell only. It proves the visual language, semantic structure, responsive layout, and safe-by-default presentation before API, realtime, or approval behaviour is introduced.

## Folder architecture

```text
apps/web/
├── app/
│   ├── globals.css   # design tokens, layout, status, focus, responsive styles
│   ├── layout.tsx    # global document shell and metadata
│   └── page.tsx      # server-rendered Life Feed fixture
├── .env.example
├── next.config.ts
├── next-env.d.ts
├── package.json
└── tsconfig.json
```

## Module responsibilities

`layout.tsx` owns browser-document concerns only. `page.tsx` owns the single static route and may contain its small presentation fixture while there is only one card. `globals.css` owns visual tokens and responsive/accessibility styles. No component, hook, store, API client, or route abstraction exists until a real second consumer appears.

## Intentional boundaries

The page contains redacted travel facts and disabled action controls. It does not claim that an approval occurred, connect to an API, open a dialog, fetch data, or invoke an external service. The displayed preview state is distinct from an execution result.

## Evolution triggers

- Extract `components/life-feed-card.tsx` when an API-backed card and a second event type share stable markup.
- Add `lib/api.ts` with typed API responses when M7 binds the documented REST endpoints.
- Add `app/events/[eventId]/page.tsx` when the event-detail endpoint and route are available.
- Add a client component only for real interaction, SSE subscription, or dialog focus management.
- Keep plain CSS until the application has repeated UI patterns that native CSS cannot reasonably maintain.

## M1 acceptance evidence

`npm run typecheck` and `npm run build` pass. The rendered page uses semantic landmarks, native disabled controls with explanatory text, visible focus styling, status words plus color, and a responsive layout without extra packages.
