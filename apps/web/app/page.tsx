const DISCLAIMER = "TrustFit Score is not a credit rating or investment advice.";

export default function Home() {
  return (
    <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col justify-center gap-6 px-6 py-24">
      <h1 className="text-4xl font-semibold tracking-tight text-navy">TrustFit</h1>
      <p className="text-lg text-ink-muted">
        Can this Indian company be trusted, is it right for us, and who in India can fill our gaps?
      </p>
      <p className="font-mono text-sm text-blue">Scaffold ready. Trust Score comes next.</p>
      <p className="text-xs text-ink-muted">{DISCLAIMER}</p>
    </main>
  );
}
