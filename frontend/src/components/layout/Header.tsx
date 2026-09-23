export default function Header() {
  return (
    <header className="bg-slate-900 text-white px-6 py-4">
      <div className="max-w-6xl mx-auto flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">Sales Intelligence Platform</h1>
          <p className="text-sm text-slate-400">Strategy& EFS — Energy, Aerospace & Defense, Automotive</p>
        </div>
        <div className="text-sm text-slate-400">v0.1 MVP</div>
      </div>
    </header>
  );
}
