import FileUploader from '../components/common/FileUploader';
import { uploadCompanies, uploadContacts } from '../api/upload';

export default function UploadPage() {
  return (
    <div className="max-w-2xl mx-auto px-4 py-6 space-y-6">
      <div>
        <h1 className="text-lg font-semibold text-slate-900">Upload Data</h1>
        <p className="text-sm text-slate-500 mt-1">
          Import companies and contacts from CSV or Excel files. Column headers are matched flexibly
          — "Company Name", "company_name", or just "Name" all work.
        </p>
      </div>

      <FileUploader
        label="Upload Companies"
        description="CSV or Excel with columns: Name (required), Industry, Sub Sector, Size, Geography, Client Status, Website, Notes"
        accept=".csv,.xlsx,.xls"
        onUpload={uploadCompanies}
      />

      <FileUploader
        label="Upload Contacts"
        description="CSV or Excel with columns: Name (required), Company (required — must match an existing company), Title, Email, Relationship Strength (1-5), Notes"
        accept=".csv,.xlsx,.xls"
        onUpload={uploadContacts}
      />
    </div>
  );
}
