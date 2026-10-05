import { NavLink, Route, Routes } from 'react-router'
import Archive from './pages/Archive'
import Home from './pages/Home'
import ThemeDetail from './pages/ThemeDetail'

export default function App() {
  return (
    <div className="min-h-screen bg-white">
      {/* Masthead */}
      <header className="bg-black text-white">
        <div className="flex w-full items-center justify-between px-4 py-3 sm:px-6 lg:px-10">
          <NavLink to="/" className="text-[14px] font-extrabold tracking-[0.18em] uppercase flex items-center gap-2 whitespace-nowrap sm:text-[17px] sm:tracking-[0.22em]">
            <span className="inline-block h-2.5 w-2.5 bg-[#e51503]" />
            Thematic Tracker
          </NavLink>
          <nav className="flex items-center gap-6">
            <span className="t-time hidden text-gray-400 sm:block">
              {new Date().toISOString().slice(0, 10)} · CLOSE EDITION
            </span>
            <NavLink
              to="/"
              end
              className={({ isActive }) =>
                `text-xs font-bold uppercase tracking-[0.14em] ${isActive ? 'text-white border-b border-white pb-0.5' : 'text-gray-500 hover:text-white'}`
              }
            >
              Today
            </NavLink>
            <NavLink
              to="/archive"
              className={({ isActive }) =>
                `text-xs font-bold uppercase tracking-[0.14em] ${isActive ? 'text-white border-b border-white pb-0.5' : 'text-gray-500 hover:text-white'}`
              }
            >
              Archive
            </NavLink>
          </nav>
        </div>
      </header>
      <div className="rule-dark" />

      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/theme/:id" element={<ThemeDetail />} />
        <Route path="/archive" element={<Archive />} />
      </Routes>

      <footer className="rule mt-16">
        <div className="w-full px-4 py-4 sm:px-6 lg:px-10">
          <p className="t-explainer">Closing prices only · Price Return · Sources inline · Not investment advice</p>
        </div>
      </footer>
    </div>
  )
}
