import { NavLink } from 'react-router-dom';

const NAV_ITEMS = [
  { to: '/', label: 'Dashboard' },
  { to: '/outreach', label: 'Outreach' },
  { to: '/signals', label: 'Signals' },
  { to: '/companies', label: 'Companies' },
  { to: '/reports', label: 'Reports' },
  { to: '/taxonomy', label: 'Taxonomy' },
  { to: '/upload', label: 'Upload' },
];

export default function Sidebar() {
  return (
    <aside className="w-52 bg-slate-800 text-white flex flex-col shrink-0">
      <div className="px-4 py-5 border-b border-slate-700">
        <h1 className="text-sm font-semibold">Sales Intelligence</h1>
        <p className="text-xs text-slate-400 mt-0.5">Strategy& EFS</p>
      </div>
      <nav className="flex-1 py-3">
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === '/'}
            className={({ isActive }) =>
              `block px-4 py-2 text-sm transition-colors ${
                isActive
                  ? 'bg-slate-700 text-white font-medium'
                  : 'text-slate-300 hover:bg-slate-700/50 hover:text-white'
              }`
            }
          >
            {item.label}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
