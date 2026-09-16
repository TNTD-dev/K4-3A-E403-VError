# VError D2

VError is a local TypeScript monolith for the Track D2 tokenization learning slice.

The browser flow is served from `public/index.html` and calls the Fastify API.
The learning orchestrator, answer key, evaluator, retry policy, citation verifier and event writer run on the server.

## Run

```bash
npm install
npm run dev
```

Open `http://localhost:3000`.

The default is `MODEL_MODE=offline`, so the complete flow works without a network or API key.
Set `MODEL_MODE=live`, `OPENAI_API_KEY` and `OPENAI_MODEL` only on the server to enable the bounded D2 Coach wording call.
The live provider is optional and always falls back to the reviewed offline templates.

## Test

```bash
npm test
npm run check
```

The answer key is server-only and is never included in the session response.
The repository contains only short, reviewed excerpts from Transcript-04, not the course data pack.
