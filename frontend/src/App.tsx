import { BrowserRouter, Routes, Route, Link } from 'react-router-dom';
import Sidebar from './components/layout/Sidebar';
import Header from './components/layout/Header';
import DashboardPage from './pages/DashboardPage';
import SignalsPage from './pages/SignalsPage';
import CompaniesPage from './pages/CompaniesPage';
import CompanyDetailPage from './pages/CompanyDetailPage';
import UploadPage from './pages/UploadPage';
import ReportsPage from './pages/ReportsPage';
import OutreachPage from './pages/OutreachPage';
import TaxonomyPage from './pages/TaxonomyPage';

function NotFound() {
  return (
    <div className="flex flex-col items-center justify-center py-24 text-center">
      <h1 className="text-2xl font-semibold text-slate-900 mb-2">Page not found</h1>
      <p className="text-sm text-slate-500 mb-6">The page you are looking for does not exist.</p>
      <Link to="/" className="text-sm text-blue-600 hover:underline">Back to Dashboard</Link>
    </div>
  );
}

function App() {
  return (
    <BrowserRouter>
      <div className="flex min-h-screen bg-slate-50">
        <Sidebar />
        <div className="flex-1 flex flex-col min-w-0">
          <Header />
          <main className="flex-1">
            <Routes>
              <Route path="/" element={<DashboardPage />} />
              <Route path="/outreach" element={<OutreachPage />} />
              <Route path="/signals" element={<SignalsPage />} />
              <Route path="/companies" element={<CompaniesPage />} />
              <Route path="/companies/:id" element={<CompanyDetailPage />} />
              <Route path="/upload" element={<UploadPage />} />
              <Route path="/reports" element={<ReportsPage />} />
              <Route path="/taxonomy" element={<TaxonomyPage />} />
              <Route path="*" element={<NotFound />} />
            </Routes>
          </main>
        </div>
      </div>
    </BrowserRouter>
  );
}

export default App;
