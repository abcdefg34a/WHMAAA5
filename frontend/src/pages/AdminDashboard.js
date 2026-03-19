import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import axios from 'axios';
import {
  Car, Search, LogOut, Users, Truck, Shield, Building2,
  CheckCircle, Clock, Download, Filter, BarChart3, AlertCircle,
  FileText, X, Eye, Lock, Unlock, Trash2, Key, MoreVertical,
  History, Database, FileSpreadsheet, HardDrive, RefreshCw,
  Archive, Play, Loader2, CloudDownload
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogFooter } from '../components/ui/dialog';
import { Badge } from '../components/ui/badge';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger, DropdownMenuSeparator } from '../components/ui/dropdown-menu';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '../components/ui/alert-dialog';
import { toast } from 'sonner';
import { Pagination } from '../components/Pagination';
import TwoFactorSetup from '../components/profile/TwoFactorSetup';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export const AdminDashboard = () => {
  const { user, logout } = useAuth();
  const [activeTab, setActiveTab] = useState('overview');
  const [stats, setStats] = useState(null);
  const [jobs, setJobs] = useState([]);
  const [users, setUsers] = useState([]);
  const [pendingServices, setPendingServices] = useState([]);
  const [pendingAuthorities, setPendingAuthorities] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');

  // Pagination state
  const [currentPage, setCurrentPage] = useState(1);
  const [totalJobs, setTotalJobs] = useState(0);
  const itemsPerPage = 50;

  // Approval dialog state
  const [selectedService, setSelectedService] = useState(null);
  const [selectedAuthority, setSelectedAuthority] = useState(null);
  const [approvalDialogOpen, setApprovalDialogOpen] = useState(false);
  const [authorityApprovalDialogOpen, setAuthorityApprovalDialogOpen] = useState(false);
  const [rejectionReason, setRejectionReason] = useState('');
  const [approving, setApproving] = useState(false);

  // User management state
  const [selectedUser, setSelectedUser] = useState(null);
  const [passwordDialogOpen, setPasswordDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [newPassword, setNewPassword] = useState('');
  const [actionLoading, setActionLoading] = useState(false);

  // Audit logs state
  const [auditLogs, setAuditLogs] = useState([]);
  const [auditLoading, setAuditLoading] = useState(false);

  // Backup state
  const [backups, setBackups] = useState([]);
  const [backupStatus, setBackupStatus] = useState(null);
  const [backupsLoading, setBackupsLoading] = useState(false);
  const [backupRunning, setBackupRunning] = useState(false);
  const [restoreDialogOpen, setRestoreDialogOpen] = useState(false);
  const [selectedBackup, setSelectedBackup] = useState(null);
  const [deleteBackupDialogOpen, setDeleteBackupDialogOpen] = useState(false);
  
  // Cloud Backup State
  const [cloudBackups, setCloudBackups] = useState([]);
  const [cloudBackupsLoading, setCloudBackupsLoading] = useState(false);
  const [cloudRestoreDialogOpen, setCloudRestoreDialogOpen] = useState(false);
  const [selectedCloudBackup, setSelectedCloudBackup] = useState(null);
  const [showCloudBackups, setShowCloudBackups] = useState(false);
  
  // Backup Health/Verification State
  const [backupHealth, setBackupHealth] = useState(null);
  const [verifyingBackups, setVerifyingBackups] = useState(false);
  
  // Backup Schedule State
  const [scheduleSettings, setScheduleSettings] = useState(null);
  const [scheduleDialogOpen, setScheduleDialogOpen] = useState(false);
  const [savingSchedule, setSavingSchedule] = useState(false);

  useEffect(() => {
    fetchData();
  }, [currentPage]);

  // Load audit logs when switching to audit tab
  useEffect(() => {
    if (activeTab === 'audit' && auditLogs.length === 0) {
      fetchAuditLogs();
    }
  }, [activeTab]);

  // Load audit logs when switching to system tab (for count display)
  useEffect(() => {
    if (activeTab === 'system' && auditLogs.length === 0) {
      fetchAuditLogs();
    }
  }, [activeTab]);

  // Load backups when switching to backups tab
  useEffect(() => {
    if (activeTab === 'backups') {
      fetchBackups();
      fetchBackupStatus();
      fetchBackupHealth();
      fetchScheduleSettings();
    }
  }, [activeTab]);

  const fetchData = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      params.append('page', currentPage.toString());
      params.append('limit', itemsPerPage.toString());
      if (searchQuery) params.append('search', searchQuery);
      if (statusFilter && statusFilter !== 'all') params.append('status', statusFilter);

      const [statsRes, jobsRes, jobsCountRes, usersRes, pendingServicesRes, pendingAuthoritiesRes] = await Promise.all([
        axios.get(`${API}/admin/stats`),
        axios.get(`${API}/admin/jobs?${params.toString()}`),
        axios.get(`${API}/admin/jobs/count?${new URLSearchParams({
          ...(searchQuery && { search: searchQuery }),
          ...(statusFilter && statusFilter !== 'all' && { status: statusFilter })
        }).toString()}`),
        axios.get(`${API}/admin/users`),
        axios.get(`${API}/admin/pending-services`),
        axios.get(`${API}/admin/pending-authorities`)
      ]);
      setStats(statsRes.data);
      setJobs(jobsRes.data);
      setTotalJobs(jobsCountRes.data.total);
      setUsers(usersRes.data);
      setPendingServices(pendingServicesRes.data);
      setPendingAuthorities(pendingAuthoritiesRes.data);
    } catch (error) {
      console.error('Error fetching data:', error);
      toast.error('Fehler beim Laden der Daten');
    } finally {
      setLoading(false);
    }
  };

  const fetchAuditLogs = async () => {
    setAuditLoading(true);
    try {
      const response = await axios.get(`${API}/admin/audit-logs?limit=100`);
      setAuditLogs(response.data);
    } catch (error) {
      console.error('Error fetching audit logs:', error);
    } finally {
      setAuditLoading(false);
    }
  };

  // ==================== BACKUP FUNKTIONEN ====================
  
  const fetchBackups = async () => {
    setBackupsLoading(true);
    try {
      const response = await axios.get(`${API}/admin/backups?limit=50`);
      setBackups(response.data);
    } catch (error) {
      console.error('Error fetching backups:', error);
      toast.error('Fehler beim Laden der Backups');
    } finally {
      setBackupsLoading(false);
    }
  };

  const fetchBackupStatus = async () => {
    try {
      const response = await axios.get(`${API}/admin/backups/system-status`);
      setBackupStatus(response.data);
    } catch (error) {
      console.error('Error fetching backup status:', error);
    }
  };

  const handleRunDatabaseBackup = async () => {
    setBackupRunning(true);
    try {
      toast.info('Datenbank-Backup wird erstellt...');
      const response = await axios.post(`${API}/admin/backups/run-database-backup`);
      if (response.data.status === 'success') {
        toast.success(`Backup erfolgreich: ${response.data.filename}`);
        fetchBackups();
        fetchBackupStatus();
      } else {
        toast.error('Backup fehlgeschlagen: ' + (response.data.error || 'Unbekannter Fehler'));
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Backup fehlgeschlagen');
    } finally {
      setBackupRunning(false);
    }
  };

  const handleRunStorageBackup = async () => {
    setBackupRunning(true);
    try {
      toast.info('Storage-Backup wird erstellt...');
      const response = await axios.post(`${API}/admin/backups/run-storage-backup`);
      if (response.data.status === 'success') {
        toast.success(`Backup erfolgreich: ${response.data.filename}`);
        fetchBackups();
        fetchBackupStatus();
      } else {
        toast.error('Backup fehlgeschlagen: ' + (response.data.error || 'Unbekannter Fehler'));
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Backup fehlgeschlagen');
    } finally {
      setBackupRunning(false);
    }
  };

  const handleRunFullBackup = async () => {
    setBackupRunning(true);
    try {
      toast.info('Komplett-Backup wird erstellt (Datenbank + Storage)...');
      const response = await axios.post(`${API}/admin/backups/run-full-backup`);
      if (response.data.status === 'success' || response.data.status === 'partial_failure') {
        toast.success('Komplett-Backup erfolgreich erstellt');
        fetchBackups();
        fetchBackupStatus();
      } else {
        toast.error('Backup fehlgeschlagen');
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Backup fehlgeschlagen');
    } finally {
      setBackupRunning(false);
    }
  };

  const handleDownloadBackup = async (backupId, filename) => {
    try {
      toast.info('Download wird vorbereitet...');
      const response = await axios.get(`${API}/admin/backups/${backupId}/download`, {
        responseType: 'blob'
      });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      toast.success('Download gestartet');
    } catch (error) {
      toast.error('Download fehlgeschlagen');
    }
  };

  const handleRestoreBackup = async () => {
    if (!selectedBackup) return;
    
    setActionLoading(true);
    try {
      const endpoint = selectedBackup.backup_type === 'database' 
        ? `${API}/admin/backups/${selectedBackup.id}/restore-database`
        : `${API}/admin/backups/${selectedBackup.id}/restore-storage`;
      
      const response = await axios.post(endpoint, { confirm: true });
      
      if (response.data.status === 'success') {
        toast.success('Wiederherstellung erfolgreich!');
        setRestoreDialogOpen(false);
        setSelectedBackup(null);
        fetchBackups();
        fetchBackupStatus();
      } else {
        toast.error('Wiederherstellung fehlgeschlagen: ' + (response.data.error || response.data.message));
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Wiederherstellung fehlgeschlagen');
    } finally {
      setActionLoading(false);
    }
  };

  const handleDeleteBackup = async () => {
    if (!selectedBackup) return;
    
    setActionLoading(true);
    try {
      const response = await axios.delete(`${API}/admin/backups/${selectedBackup.id}`);
      if (response.data.status === 'success') {
        toast.success('Backup gelöscht');
        setDeleteBackupDialogOpen(false);
        setSelectedBackup(null);
        fetchBackups();
        fetchBackupStatus();
      } else {
        toast.error('Löschen fehlgeschlagen');
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Löschen fehlgeschlagen');
    } finally {
      setActionLoading(false);
    }
  };

  const formatBytes = (bytes) => {
    if (!bytes || bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleString('de-DE', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  // ==================== CLOUD BACKUP FUNKTIONEN ====================
  
  const fetchCloudBackups = async () => {
    setCloudBackupsLoading(true);
    try {
      const response = await axios.get(`${API}/admin/backups/cloud`);
      setCloudBackups(response.data);
    } catch (error) {
      console.error('Error fetching cloud backups:', error);
      toast.error('Fehler beim Laden der Cloud-Backups');
    } finally {
      setCloudBackupsLoading(false);
    }
  };

  const handleRestoreFromCloud = async () => {
    if (!selectedCloudBackup) return;
    
    setActionLoading(true);
    try {
      toast.info('Backup wird von Supabase Cloud geladen...');
      const response = await axios.post(`${API}/admin/backups/cloud/restore`, {
        cloud_path: selectedCloudBackup.path,
        confirm: true
      });
      
      if (response.data.status === 'success') {
        toast.success(`Cloud-Wiederherstellung erfolgreich! ${response.data.collections_restored?.length || 0} Collections wiederhergestellt.`);
        setCloudRestoreDialogOpen(false);
        setSelectedCloudBackup(null);
        fetchBackups();
        fetchBackupStatus();
      } else {
        toast.error('Wiederherstellung fehlgeschlagen: ' + (response.data.message || 'Unbekannter Fehler'));
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Cloud-Wiederherstellung fehlgeschlagen');
    } finally {
      setActionLoading(false);
    }
  };

  // ==================== BACKUP VERIFIZIERUNG ====================
  
  const fetchBackupHealth = async () => {
    try {
      const response = await axios.get(`${API}/admin/backups/health`);
      setBackupHealth(response.data);
    } catch (error) {
      console.error('Error fetching backup health:', error);
    }
  };

  const handleVerifyAllBackups = async () => {
    setVerifyingBackups(true);
    try {
      toast.info('Alle Backups werden überprüft...');
      const response = await axios.post(`${API}/admin/backups/verify-all`);
      
      if (response.data.invalid === 0) {
        toast.success(`✅ Alle ${response.data.valid} Backups sind gültig!`);
      } else {
        toast.warning(`⚠️ ${response.data.invalid} von ${response.data.total} Backups sind beschädigt!`);
      }
      
      fetchBackupHealth();
      fetchBackups();
    } catch (error) {
      toast.error('Verifizierung fehlgeschlagen');
    } finally {
      setVerifyingBackups(false);
    }
  };

  const handleVerifySingleBackup = async (backupId) => {
    try {
      toast.info('Backup wird überprüft...');
      const response = await axios.post(`${API}/admin/backups/${backupId}/verify`);
      
      if (response.data.valid) {
        toast.success('✅ Backup ist gültig!');
      } else {
        toast.error(`❌ Backup beschädigt: ${response.data.errors?.[0] || 'Unbekannter Fehler'}`);
      }
      
      fetchBackups();
      fetchBackupHealth();
    } catch (error) {
      toast.error('Verifizierung fehlgeschlagen');
    }
  };

  // ==================== BACKUP ZEITPLAN ====================
  
  const fetchScheduleSettings = async () => {
    try {
      const response = await axios.get(`${API}/admin/backups/schedule`);
      setScheduleSettings(response.data);
    } catch (error) {
      console.error('Error fetching schedule settings:', error);
    }
  };

  const handleSaveSchedule = async () => {
    setSavingSchedule(true);
    try {
      const response = await axios.put(`${API}/admin/backups/schedule`, scheduleSettings);
      
      if (response.data.status === 'success') {
        toast.success('Zeitplan-Einstellungen gespeichert!');
        setScheduleDialogOpen(false);
        fetchBackupStatus();
      } else {
        toast.error(response.data.message || 'Fehler beim Speichern');
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Fehler beim Speichern');
    } finally {
      setSavingSchedule(false);
    }
  };

  const formatTimeString = (hour, minute) => {
    return `${hour.toString().padStart(2, '0')}:${minute.toString().padStart(2, '0')} Uhr`;
  };

  const getFrequencyLabel = (freq) => {
    switch (freq) {
      case 'every_6h': return 'Alle 6 Stunden';
      case 'every_12h': return 'Alle 12 Stunden';
      default: return 'Täglich';
    }
  };

  const handleExportExcel = async () => {
    try {
      toast.info('Excel wird erstellt...');
      const response = await axios.get(`${API}/export/jobs/excel`, {
        responseType: 'blob'
      });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `auftraege_${new Date().toISOString().split('T')[0]}.xlsx`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      toast.success('Excel erfolgreich heruntergeladen');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Export fehlgeschlagen');
    }
  };

  const handleSearch = async () => {
    setCurrentPage(1); // Reset to first page on new search
    try {
      const params = new URLSearchParams();
      params.append('page', '1');
      params.append('limit', itemsPerPage.toString());
      if (searchQuery) params.append('search', searchQuery);
      if (statusFilter && statusFilter !== 'all') params.append('status', statusFilter);

      const [jobsRes, countRes] = await Promise.all([
        axios.get(`${API}/admin/jobs?${params.toString()}`),
        axios.get(`${API}/admin/jobs/count?${new URLSearchParams({
          ...(searchQuery && { search: searchQuery }),
          ...(statusFilter && statusFilter !== 'all' && { status: statusFilter })
        }).toString()}`)
      ]);
      setJobs(jobsRes.data);
      setTotalJobs(countRes.data.total);
    } catch (error) {
      toast.error('Fehler bei der Suche');
    }
  };

  const handlePageChange = (page) => {
    setCurrentPage(page);
  };

  const handleApproval = async (approved) => {
    if (!selectedService) return;
    setApproving(true);

    try {
      await axios.post(`${API}/admin/approve-service/${selectedService.id}`, {
        approved,
        rejection_reason: approved ? null : rejectionReason
      });

      toast.success(approved ? 'Abschleppdienst freigeschaltet' : 'Abschleppdienst abgelehnt');
      setApprovalDialogOpen(false);
      setSelectedService(null);
      setRejectionReason('');
      fetchData();
    } catch (error) {
      toast.error('Fehler bei der Verarbeitung');
    } finally {
      setApproving(false);
    }
  };

  const handleAuthorityApproval = async (approved) => {
    if (!selectedAuthority) return;
    setApproving(true);

    try {
      await axios.post(`${API}/admin/approve-authority/${selectedAuthority.id}`, {
        approved,
        rejection_reason: approved ? null : rejectionReason
      });

      toast.success(approved ? 'Behörde freigeschaltet' : 'Behörde abgelehnt');
      setAuthorityApprovalDialogOpen(false);
      setSelectedAuthority(null);
      setRejectionReason('');
      fetchData();
    } catch (error) {
      toast.error('Fehler bei der Verarbeitung');
    } finally {
      setApproving(false);
    }
  };

  const openApprovalDialog = (service) => {
    setSelectedService(service);
    setApprovalDialogOpen(true);
  };

  const openAuthorityApprovalDialog = (authority) => {
    setSelectedAuthority(authority);
    setAuthorityApprovalDialogOpen(true);
  };

  // User Management Functions
  const handleUpdatePassword = async () => {
    if (!selectedUser || !newPassword) return;
    if (newPassword.length < 8) {
      toast.error('Passwort muss mindestens 8 Zeichen haben');
      return;
    }

    setActionLoading(true);
    try {
      await axios.patch(`${API}/admin/users/${selectedUser.id}/password`, {
        new_password: newPassword
      });
      toast.success(`Passwort für ${selectedUser.name} wurde aktualisiert`);
      setPasswordDialogOpen(false);
      setSelectedUser(null);
      setNewPassword('');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Fehler beim Aktualisieren des Passworts');
    } finally {
      setActionLoading(false);
    }
  };

  const handleBlockUser = async (targetUser, block) => {
    setActionLoading(true);
    try {
      await axios.patch(`${API}/admin/users/${targetUser.id}/block`, {
        blocked: block
      });
      toast.success(`${targetUser.name} wurde ${block ? 'gesperrt' : 'entsperrt'}`);
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Fehler bei der Aktion');
    } finally {
      setActionLoading(false);
    }
  };

  const handleDeleteUser = async () => {
    if (!selectedUser) return;

    setActionLoading(true);
    try {
      await axios.delete(`${API}/admin/users/${selectedUser.id}`);
      toast.success(`${selectedUser.name} wurde permanent gelöscht`);
      setDeleteDialogOpen(false);
      setSelectedUser(null);
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Fehler beim Löschen');
    } finally {
      setActionLoading(false);
    }
  };

  const openPasswordDialog = (u) => {
    setSelectedUser(u);
    setNewPassword('');
    setPasswordDialogOpen(true);
  };

  const openDeleteDialog = (u) => {
    setSelectedUser(u);
    setDeleteDialogOpen(true);
  };

  const getStatusBadge = (status) => {
    const statusConfig = {
      pending: { label: 'Ausstehend', class: 'status-pending' },
      assigned: { label: 'Zugewiesen', class: 'status-assigned' },
      on_site: { label: 'Vor Ort', class: 'status-on_site' },
      towed: { label: 'Abgeschleppt', class: 'status-towed' },
      in_yard: { label: 'Im Hof', class: 'status-in_yard' },
      released: { label: 'Abgeholt', class: 'status-released' }
    };
    const config = statusConfig[status] || { label: status, class: 'bg-gray-500' };
    return (
      <span className={`px-2 py-1 rounded-full text-xs font-medium ${config.class}`}>
        {config.label}
      </span>
    );
  };

  const getRoleBadge = (role) => {
    const roleConfig = {
      admin: { label: 'Admin', class: 'bg-purple-100 text-purple-700' },
      authority: { label: 'Behörde', class: 'bg-blue-100 text-blue-700' },
      towing_service: { label: 'Abschleppdienst', class: 'bg-orange-100 text-orange-700' }
    };
    const config = roleConfig[role] || { label: role, class: 'bg-gray-100 text-gray-700' };
    return (
      <span className={`px-2 py-1 rounded-full text-xs font-medium ${config.class}`}>
        {config.label}
      </span>
    );
  };

  const getApprovalBadge = (status) => {
    if (status === 'approved') {
      return <Badge className="bg-green-100 text-green-700">Freigeschaltet</Badge>;
    } else if (status === 'rejected') {
      return <Badge className="bg-red-100 text-red-700">Abgelehnt</Badge>;
    } else if (status === 'pending') {
      return <Badge className="bg-yellow-100 text-yellow-700">Ausstehend</Badge>;
    }
    return null;
  };

  const getBlockedBadge = (isBlocked) => {
    if (isBlocked) {
      return <Badge className="bg-red-100 text-red-700">Gesperrt</Badge>;
    }
    return null;
  };

  const downloadPDF = async (jobId) => {
    try {
      const tokenRes = await axios.get(`${API}/jobs/${jobId}/pdf/token`);
      window.open(`${API}/jobs/${jobId}/pdf?token=${tokenRes.data.token}`, '_blank');
    } catch (error) {
      toast.error('Fehler beim Herunterladen des PDFs');
    }
  };

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center gap-3">
              <div className="bg-purple-600 p-2 rounded-lg">
                <Shield className="h-6 w-6 text-white" />
              </div>
              <div>
                <h1 className="font-bold text-lg text-slate-900" style={{ fontFamily: 'Chivo, sans-serif' }}>
                  Admin Dashboard
                </h1>
                <p className="text-xs text-slate-500">Systemübersicht</p>
              </div>
            </div>

            <div className="flex items-center gap-3">
              {stats?.pending_approvals > 0 && (
                <div
                  className="bg-red-100 text-red-700 px-3 py-1 rounded-full text-sm font-medium cursor-pointer flex items-center gap-2"
                  onClick={() => setActiveTab('approvals')}
                >
                  <AlertCircle className="h-4 w-4" />
                  {stats.pending_approvals} Freischaltung(en)
                </div>
              )}
              <span className="hidden md:block text-sm text-slate-600">
                {user?.name}
              </span>
              <Button
                data-testid="logout-btn"
                variant="outline"
                size="sm"
                onClick={logout}
              >
                <LogOut className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 py-6">
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="mb-6">
            <TabsTrigger data-testid="tab-overview" value="overview" className="flex items-center gap-2">
              <BarChart3 className="h-4 w-4" />
              Übersicht
            </TabsTrigger>
            <TabsTrigger data-testid="tab-approvals" value="approvals" className="flex items-center gap-2 relative">
              <AlertCircle className="h-4 w-4" />
              Freischaltungen
              {(pendingServices.length + pendingAuthorities.length) > 0 && (
                <span className="absolute -top-1 -right-1 bg-red-500 text-white text-xs w-5 h-5 rounded-full flex items-center justify-center">
                  {pendingServices.length + pendingAuthorities.length}
                </span>
              )}
            </TabsTrigger>
            <TabsTrigger data-testid="tab-all-jobs" value="jobs" className="flex items-center gap-2">
              <Car className="h-4 w-4" />
              Alle Aufträge
            </TabsTrigger>
            <TabsTrigger data-testid="tab-users" value="users" className="flex items-center gap-2">
              <Users className="h-4 w-4" />
              Benutzer
            </TabsTrigger>
            <TabsTrigger
              data-testid="tab-audit"
              value="audit"
              className="flex items-center gap-2"
            >
              <History className="h-4 w-4" />
              Audit-Log
            </TabsTrigger>
            <TabsTrigger
              data-testid="tab-system"
              value="system"
              className="flex items-center gap-2"
            >
              <Database className="h-4 w-4" />
              System
            </TabsTrigger>
            <TabsTrigger
              data-testid="tab-backups"
              value="backups"
              className="flex items-center gap-2"
            >
              <HardDrive className="h-4 w-4" />
              Backups
            </TabsTrigger>
          </TabsList>

          {/* Overview Tab */}
          <TabsContent value="overview">
            {loading ? (
              <div className="flex justify-center py-8">
                <div className="loading-spinner"></div>
              </div>
            ) : stats && (
              <>
                {stats.pending_approvals > 0 && (
                  <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 mb-6 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <AlertCircle className="h-6 w-6 text-amber-600" />
                      <div>
                        <p className="font-medium text-amber-900">{stats.pending_approvals} Abschleppdienst(e) warten auf Freischaltung</p>
                        <p className="text-sm text-amber-700">Bitte prüfen Sie die Registrierungen und Gewerbenachweise</p>
                      </div>
                    </div>
                    <Button onClick={() => setActiveTab('approvals')} className="bg-amber-600 hover:bg-amber-700">
                      Jetzt prüfen
                    </Button>
                  </div>
                )}

                <div className="stats-grid mb-8">
                  <Card>
                    <CardContent className="pt-6">
                      <div className="flex items-center gap-4">
                        <div className="bg-blue-100 p-3 rounded-lg">
                          <Car className="h-6 w-6 text-blue-600" />
                        </div>
                        <div>
                          <p className="stat-value">{stats.total_jobs}</p>
                          <p className="stat-label">Gesamt Aufträge</p>
                        </div>
                      </div>
                    </CardContent>
                  </Card>

                  <Card>
                    <CardContent className="pt-6">
                      <div className="flex items-center gap-4">
                        <div className="bg-yellow-100 p-3 rounded-lg">
                          <Clock className="h-6 w-6 text-yellow-600" />
                        </div>
                        <div>
                          <p className="stat-value">{stats.pending_jobs}</p>
                          <p className="stat-label">In Bearbeitung</p>
                        </div>
                      </div>
                    </CardContent>
                  </Card>

                  <Card>
                    <CardContent className="pt-6">
                      <div className="flex items-center gap-4">
                        <div className="bg-orange-100 p-3 rounded-lg">
                          <Building2 className="h-6 w-6 text-orange-600" />
                        </div>
                        <div>
                          <p className="stat-value">{stats.in_yard_jobs}</p>
                          <p className="stat-label">Im Hof</p>
                        </div>
                      </div>
                    </CardContent>
                  </Card>

                  <Card>
                    <CardContent className="pt-6">
                      <div className="flex items-center gap-4">
                        <div className="bg-green-100 p-3 rounded-lg">
                          <CheckCircle className="h-6 w-6 text-green-600" />
                        </div>
                        <div>
                          <p className="stat-value">{stats.released_jobs}</p>
                          <p className="stat-label">Abgeholt</p>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </div>

                <div className="grid md:grid-cols-2 gap-6">
                  <Card>
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2">
                        <Shield className="h-5 w-5" />
                        Behörden
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <p className="stat-value">{stats.total_authorities}</p>
                      <p className="stat-label">Registrierte Behörden</p>
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2">
                        <Truck className="h-5 w-5" />
                        Abschleppdienste
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <p className="stat-value">{stats.total_services}</p>
                      <p className="stat-label">Freigeschaltete Abschleppdienste</p>
                    </CardContent>
                  </Card>
                </div>
              </>
            )}
          </TabsContent>

          {/* Approvals Tab */}
          <TabsContent value="approvals">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <AlertCircle className="h-5 w-5" />
                  Ausstehende Freischaltungen
                </CardTitle>
              </CardHeader>
              <CardContent>
                {loading ? (
                  <div className="flex justify-center py-8">
                    <div className="loading-spinner"></div>
                  </div>
                ) : (pendingServices.length === 0 && pendingAuthorities.length === 0) ? (
                  <div className="empty-state">
                    <CheckCircle className="empty-state-icon text-green-500" />
                    <p>Keine ausstehenden Freischaltungen</p>
                  </div>
                ) : (
                  <div className="space-y-6">
                    {/* Pending Authorities */}
                    {pendingAuthorities.length > 0 && (
                      <div>
                        <h3 className="font-semibold text-lg mb-4 flex items-center gap-2">
                          <Shield className="h-5 w-5 text-blue-500" />
                          Behörden ({pendingAuthorities.length})
                        </h3>
                        <div className="space-y-4">
                          {pendingAuthorities.map(authority => (
                            <div
                              key={authority.id}
                              className="border border-blue-200 rounded-lg p-4 hover:shadow-md transition-shadow bg-blue-50"
                            >
                              <div className="flex justify-between items-start">
                                <div className="space-y-2">
                                  <div className="flex items-center gap-3">
                                    <Shield className="h-6 w-6 text-blue-500" />
                                    <div>
                                      <h3 className="font-bold text-lg">{authority.authority_name}</h3>
                                      <p className="text-sm text-slate-500">{authority.email}</p>
                                    </div>
                                  </div>
                                  <div className="grid sm:grid-cols-2 gap-4 text-sm mt-4">
                                    <div>
                                      <p className="text-slate-500">Ansprechpartner</p>
                                      <p className="font-medium">{authority.name}</p>
                                    </div>
                                    <div>
                                      <p className="text-slate-500">Abteilung</p>
                                      <p className="font-medium">{authority.department || '-'}</p>
                                    </div>
                                    <div>
                                      <p className="text-slate-500">Dienstnummer</p>
                                      <p className="font-mono font-medium">{authority.dienstnummer}</p>
                                    </div>
                                    <div>
                                      <p className="text-slate-500">Registriert am</p>
                                      <p className="font-medium">{new Date(authority.created_at).toLocaleDateString('de-DE')}</p>
                                    </div>
                                  </div>
                                </div>
                                <Button
                                  onClick={() => openAuthorityApprovalDialog(authority)}
                                  className="bg-blue-600 hover:bg-blue-700"
                                >
                                  <Eye className="h-4 w-4 mr-2" />
                                  Prüfen
                                </Button>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Pending Services */}
                    {pendingServices.length > 0 && (
                      <div>
                        <h3 className="font-semibold text-lg mb-4 flex items-center gap-2">
                          <Truck className="h-5 w-5 text-orange-500" />
                          Abschleppdienste ({pendingServices.length})
                        </h3>
                        <div className="space-y-4">
                          {pendingServices.map(service => (
                            <div
                              key={service.id}
                              className="border border-orange-200 rounded-lg p-4 hover:shadow-md transition-shadow bg-orange-50"
                            >
                              <div className="flex justify-between items-start">
                                <div className="space-y-2">
                                  <div className="flex items-center gap-3">
                                    <Truck className="h-6 w-6 text-orange-500" />
                                    <div>
                                      <h3 className="font-bold text-lg">{service.company_name}</h3>
                                      <p className="text-sm text-slate-500">{service.email}</p>
                                    </div>
                                  </div>
                                  <div className="grid sm:grid-cols-2 gap-4 text-sm mt-4">
                                    <div>
                                      <p className="text-slate-500">Ansprechpartner</p>
                                      <p className="font-medium">{service.name}</p>
                                    </div>
                                    <div>
                                      <p className="text-slate-500">Telefon</p>
                                      <p className="font-medium">{service.phone}</p>
                                    </div>
                                    <div>
                                      <p className="text-slate-500">Hof-Adresse</p>
                                      <p className="font-medium">{service.yard_address}</p>
                                    </div>
                                    <div>
                                      <p className="text-slate-500">Öffnungszeiten</p>
                                      <p className="font-medium">{service.opening_hours}</p>
                                    </div>
                                  </div>
                                </div>
                                <Button
                                  onClick={() => openApprovalDialog(service)}
                                  className="bg-orange-500 hover:bg-orange-600"
                                >
                                  <Eye className="h-4 w-4 mr-2" />
                                  Prüfen
                                </Button>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* Jobs Tab */}
          <TabsContent value="jobs">
            <Card>
              <CardHeader>
                <div className="flex flex-col md:flex-row gap-4">
                  <div className="flex-1 relative">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
                    <Input
                      data-testid="admin-search-input"
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                      placeholder="Kennzeichen, FIN oder Auftragsnummer suchen..."
                      className="pl-10"
                    />
                  </div>
                  <Select value={statusFilter} onValueChange={setStatusFilter}>
                    <SelectTrigger data-testid="admin-status-filter" className="w-full md:w-48">
                      <Filter className="h-4 w-4 mr-2" />
                      <SelectValue placeholder="Status filtern" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">Alle Status</SelectItem>
                      <SelectItem value="pending">Ausstehend</SelectItem>
                      <SelectItem value="assigned">Zugewiesen</SelectItem>
                      <SelectItem value="on_site">Vor Ort</SelectItem>
                      <SelectItem value="towed">Abgeschleppt</SelectItem>
                      <SelectItem value="in_yard">Im Hof</SelectItem>
                      <SelectItem value="released">Abgeholt</SelectItem>
                    </SelectContent>
                  </Select>
                  <Button data-testid="admin-search-btn" onClick={handleSearch}>
                    <Search className="h-4 w-4 mr-2" />
                    Suchen
                  </Button>
                </div>
                {/* Export Button */}
                <div className="flex gap-2 mt-4 pt-4 border-t">
                  <Button variant="outline" size="sm" onClick={handleExportExcel}>
                    <FileSpreadsheet className="h-4 w-4 mr-2" />
                    Excel Export
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                {loading ? (
                  <div className="flex justify-center py-8">
                    <div className="loading-spinner"></div>
                  </div>
                ) : jobs.length === 0 ? (
                  <div className="empty-state">
                    <Car className="empty-state-icon" />
                    <p>Keine Aufträge gefunden</p>
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>Auftragsnr.</th>
                          <th>Kennzeichen</th>
                          <th>Status</th>
                          <th>Behörde</th>
                          <th>Dienstnr.</th>
                          <th>Abschleppdienst</th>
                          <th>Erstellt</th>
                          <th>Aktionen</th>
                        </tr>
                      </thead>
                      <tbody>
                        {jobs.map(job => {
                          return (
                            <tr key={job.id}>
                              <td className="font-mono text-sm">{job.job_number}</td>
                              <td className="font-bold">{job.license_plate}</td>
                              <td>{getStatusBadge(job.status)}</td>
                              <td>{job.created_by_authority || job.created_by_name}</td>
                              <td>
                                {job.created_by_dienstnummer ? (
                                  <span className="font-mono text-xs px-2 py-1 bg-blue-100 text-blue-700 rounded">
                                    {job.created_by_dienstnummer}
                                  </span>
                                ) : '-'}
                              </td>
                              <td>{job.assigned_service_name || '-'}</td>
                              <td>{new Date(job.created_at).toLocaleDateString('de-DE')}</td>
                              <td>
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => downloadPDF(job.id)}
                                >
                                  <Download className="h-4 w-4" />
                                </Button>
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                )}

                {/* Pagination */}
                {!loading && jobs.length > 0 && (
                  <Pagination
                    currentPage={currentPage}
                    totalPages={Math.ceil(totalJobs / itemsPerPage)}
                    totalItems={totalJobs}
                    itemsPerPage={itemsPerPage}
                    onPageChange={handlePageChange}
                  />
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* Users Tab */}
          <TabsContent value="users">
            <Card>
              <CardHeader>
                <CardTitle>Benutzerverwaltung</CardTitle>
              </CardHeader>
              <CardContent>
                {loading ? (
                  <div className="flex justify-center py-8">
                    <div className="loading-spinner"></div>
                  </div>
                ) : users.length === 0 ? (
                  <div className="empty-state">
                    <Users className="empty-state-icon" />
                    <p>Keine Benutzer gefunden</p>
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>Name</th>
                          <th>E-Mail</th>
                          <th>Rolle</th>
                          <th>Organisation</th>
                          <th>Status</th>
                          <th>Registriert</th>
                          <th>Aktionen</th>
                        </tr>
                      </thead>
                      <tbody>
                        {users.map(u => {
                          return (
                            <tr key={u.id} className={u.is_blocked ? 'opacity-60 bg-red-50' : ''}>
                              <td className="font-medium">{u.name}</td>
                              <td>{u.email}</td>
                              <td>{getRoleBadge(u.role)}</td>
                              <td>{u.authority_name || u.company_name || '-'}</td>
                              <td>
                                <div className="flex gap-1 flex-wrap">
                                  {u.role === 'towing_service' && getApprovalBadge(u.approval_status)}
                                  {getBlockedBadge(u.is_blocked)}
                                </div>
                              </td>
                              <td>{new Date(u.created_at).toLocaleDateString('de-DE')}</td>
                              <td>
                                {u.role !== 'admin' && (
                                  <DropdownMenu>
                                    <DropdownMenuTrigger asChild>
                                      <Button variant="ghost" size="sm">
                                        <MoreVertical className="h-4 w-4" />
                                      </Button>
                                    </DropdownMenuTrigger>
                                    <DropdownMenuContent align="end">
                                      <DropdownMenuItem onClick={() => openPasswordDialog(u)}>
                                        <Key className="h-4 w-4 mr-2" />
                                        Passwort ändern
                                      </DropdownMenuItem>
                                      <DropdownMenuSeparator />
                                      {u.is_blocked ? (
                                        <DropdownMenuItem onClick={() => handleBlockUser(u, false)}>
                                          <Unlock className="h-4 w-4 mr-2" />
                                          Entsperren
                                        </DropdownMenuItem>
                                      ) : (
                                        <DropdownMenuItem
                                          onClick={() => handleBlockUser(u, true)}
                                          className="text-orange-600"
                                        >
                                          <Lock className="h-4 w-4 mr-2" />
                                          Sperren
                                        </DropdownMenuItem>
                                      )}
                                      <DropdownMenuSeparator />
                                      <DropdownMenuItem
                                        onClick={() => openDeleteDialog(u)}
                                        className="text-red-600"
                                      >
                                        <Trash2 className="h-4 w-4 mr-2" />
                                        Löschen
                                      </DropdownMenuItem>
                                    </DropdownMenuContent>
                                  </DropdownMenu>
                                )}
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* Audit Log Tab */}
          <TabsContent value="audit">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <History className="h-5 w-5" />
                  Audit-Log
                </CardTitle>
                <CardDescription>
                  Alle Aktionen im System werden protokolliert
                </CardDescription>
              </CardHeader>
              <CardContent>
                {auditLoading ? (
                  <div className="flex justify-center py-8">
                    <div className="loading-spinner"></div>
                  </div>
                ) : auditLogs.length === 0 ? (
                  <div className="empty-state">
                    <History className="empty-state-icon" />
                    <p>Keine Audit-Einträge vorhanden</p>
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>Zeitpunkt</th>
                          <th>Aktion</th>
                          <th>Benutzer</th>
                          <th>Details</th>
                        </tr>
                      </thead>
                      <tbody>
                        {auditLogs.map(log => {
                          return (
                            <tr key={log.id}>
                              <td className="whitespace-nowrap text-sm">
                                {new Date(log.timestamp).toLocaleString('de-DE')}
                              </td>
                              <td>
                                <span className="px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded font-medium">
                                  {log.action}
                                </span>
                              </td>
                              <td className="text-sm">{log.user_name}</td>
                              <td className="text-sm text-slate-500 max-w-xs truncate">
                                {JSON.stringify(log.details)}
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* System Tab - Vereinfacht */}
          <TabsContent value="system">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <BarChart3 className="h-5 w-5" />
                  System-Übersicht
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-6">
                {/* Statistiken */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="p-4 bg-slate-50 rounded-lg text-center">
                    <p className="text-2xl font-bold text-slate-900">{stats?.total_jobs || 0}</p>
                    <p className="text-sm text-slate-500">Aufträge gesamt</p>
                  </div>
                  <div className="p-4 bg-slate-50 rounded-lg text-center">
                    <p className="text-2xl font-bold text-slate-900">{stats?.in_yard_jobs || 0}</p>
                    <p className="text-sm text-slate-500">Im Hof</p>
                  </div>
                  <div className="p-4 bg-slate-50 rounded-lg text-center">
                    <p className="text-2xl font-bold text-slate-900">{users.length}</p>
                    <p className="text-sm text-slate-500">Benutzer</p>
                  </div>
                  <div className="p-4 bg-slate-50 rounded-lg text-center">
                    <p className="text-2xl font-bold text-slate-900">{auditLogs.length}+</p>
                    <p className="text-sm text-slate-500">Audit-Einträge</p>
                  </div>
                </div>

                {/* Export */}
                <div className="pt-4 border-t">
                  <h4 className="font-semibold mb-3">Daten exportieren</h4>
                  <p className="text-sm text-slate-500 mb-4">
                    Exportieren Sie alle Aufträge als Excel-Datei für Ihre Buchhaltung oder Berichte.
                  </p>
                  <Button onClick={handleExportExcel} className="bg-green-600 hover:bg-green-700">
                    <FileSpreadsheet className="h-4 w-4 mr-2" />
                    Alle Aufträge exportieren (Excel)
                  </Button>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Backups Tab */}
          <TabsContent value="backups">
            <div className="space-y-6">
              {/* Backup Status KPI Cards */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <Card>
                  <CardContent className="p-4">
                    <div className="flex items-center gap-3">
                      <div className="p-2 bg-blue-100 rounded-lg">
                        <Database className="h-5 w-5 text-blue-600" />
                      </div>
                      <div>
                        <p className="text-xs text-slate-500">Letztes DB-Backup</p>
                        <p className="font-semibold text-sm">
                          {backupStatus?.last_database_backup?.date 
                            ? formatDate(backupStatus.last_database_backup.date)
                            : 'Noch keins'}
                        </p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="p-4">
                    <div className="flex items-center gap-3">
                      <div className="p-2 bg-green-100 rounded-lg">
                        <Archive className="h-5 w-5 text-green-600" />
                      </div>
                      <div>
                        <p className="text-xs text-slate-500">Letztes Storage-Backup</p>
                        <p className="font-semibold text-sm">
                          {backupStatus?.last_storage_backup?.date 
                            ? formatDate(backupStatus.last_storage_backup.date)
                            : 'Noch keins'}
                        </p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="p-4">
                    <div className="flex items-center gap-3">
                      <div className="p-2 bg-amber-100 rounded-lg">
                        <HardDrive className="h-5 w-5 text-amber-600" />
                      </div>
                      <div>
                        <p className="text-xs text-slate-500">Gesamt-Backups</p>
                        <p className="font-semibold text-sm">
                          {backupStatus?.total_backups || 0} Dateien
                        </p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="p-4">
                    <div className="flex items-center gap-3">
                      <div className={`p-2 rounded-lg ${backupStatus?.supabase_enabled ? 'bg-green-100' : 'bg-red-100'}`}>
                        <CloudDownload className={`h-5 w-5 ${backupStatus?.supabase_enabled ? 'text-green-600' : 'text-red-600'}`} />
                      </div>
                      <div>
                        <p className="text-xs text-slate-500">Cloud-Sicherung</p>
                        <p className="font-semibold text-sm">
                          {backupStatus?.supabase_enabled 
                            ? `${backupStatus?.supabase_backups || 0} in Cloud`
                            : 'Nicht aktiv'}
                        </p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </div>

              {/* Supabase Status Banner */}
              {backupStatus?.supabase_enabled && (
                <div className="bg-green-50 border border-green-200 rounded-lg p-4 flex items-center gap-3">
                  <CheckCircle className="h-5 w-5 text-green-600" />
                  <div>
                    <p className="font-medium text-green-900">Cloud-Sicherung aktiv</p>
                    <p className="text-sm text-green-700">
                      Backups werden automatisch zu Supabase Storage kopiert. Ihre Daten sind auch bei Server-Ausfall sicher.
                    </p>
                  </div>
                </div>
              )}

              {/* Backup Health Warning */}
              {backupHealth?.health_status === 'warning' && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                  <div className="flex items-center gap-3">
                    <AlertCircle className="h-5 w-5 text-red-600" />
                    <div className="flex-1">
                      <p className="font-medium text-red-900">⚠️ Beschädigte Backups gefunden!</p>
                      <p className="text-sm text-red-700">
                        {backupHealth.verified_invalid} von {backupHealth.total_backups} Backups sind beschädigt oder nicht lesbar.
                      </p>
                      {backupHealth.invalid_backups?.length > 0 && (
                        <ul className="mt-2 text-sm text-red-600">
                          {backupHealth.invalid_backups.map((b, i) => (
                            <li key={i}>• {b.filename}: {b.error}</li>
                          ))}
                        </ul>
                      )}
                    </div>
                    <Button
                      variant="outline"
                      size="sm"
                      className="border-red-300 text-red-600 hover:bg-red-100"
                      onClick={handleVerifyAllBackups}
                      disabled={verifyingBackups}
                    >
                      {verifyingBackups ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Erneut prüfen'}
                    </Button>
                  </div>
                </div>
              )}

              {/* Backup Verification Card */}
              <Card>
                <CardHeader className="flex flex-row items-center justify-between">
                  <div>
                    <CardTitle className="flex items-center gap-2">
                      <Shield className="h-5 w-5 text-blue-600" />
                      Backup-Integrität
                    </CardTitle>
                    <CardDescription>
                      Überprüfen Sie, ob alle Backups gültig und wiederherstellbar sind
                    </CardDescription>
                  </div>
                  <Button 
                    onClick={handleVerifyAllBackups}
                    disabled={verifyingBackups}
                    variant="outline"
                  >
                    {verifyingBackups ? (
                      <>
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                        Prüfe...
                      </>
                    ) : (
                      <>
                        <Shield className="h-4 w-4 mr-2" />
                        Alle Backups prüfen
                      </>
                    )}
                  </Button>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div className="text-center p-3 bg-slate-50 rounded-lg">
                      <p className="text-2xl font-bold text-slate-700">{backupHealth?.total_backups || 0}</p>
                      <p className="text-xs text-slate-500">Gesamt</p>
                    </div>
                    <div className="text-center p-3 bg-green-50 rounded-lg">
                      <p className="text-2xl font-bold text-green-600">{backupHealth?.verified_valid || 0}</p>
                      <p className="text-xs text-green-600">Gültig</p>
                    </div>
                    <div className="text-center p-3 bg-red-50 rounded-lg">
                      <p className="text-2xl font-bold text-red-600">{backupHealth?.verified_invalid || 0}</p>
                      <p className="text-xs text-red-600">Beschädigt</p>
                    </div>
                    <div className="text-center p-3 bg-amber-50 rounded-lg">
                      <p className="text-2xl font-bold text-amber-600">{backupHealth?.not_verified || 0}</p>
                      <p className="text-xs text-amber-600">Nicht geprüft</p>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Manual Backup Actions */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Play className="h-5 w-5" />
                    Manuelles Backup
                  </CardTitle>
                  <CardDescription>
                    Starten Sie sofort ein Backup der Datenbank oder Dateien
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="flex flex-wrap gap-3">
                    <Button 
                      onClick={handleRunDatabaseBackup} 
                      disabled={backupRunning}
                      className="bg-blue-600 hover:bg-blue-700"
                    >
                      {backupRunning ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Database className="h-4 w-4 mr-2" />}
                      Datenbank-Backup jetzt starten
                    </Button>
                    <Button 
                      onClick={handleRunStorageBackup}
                      disabled={backupRunning}
                      className="bg-green-600 hover:bg-green-700"
                    >
                      {backupRunning ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Archive className="h-4 w-4 mr-2" />}
                      Storage-Backup jetzt starten
                    </Button>
                    <Button 
                      onClick={handleRunFullBackup}
                      disabled={backupRunning}
                      className="bg-orange-600 hover:bg-orange-700"
                    >
                      {backupRunning ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <HardDrive className="h-4 w-4 mr-2" />}
                      Komplett-Backup jetzt starten
                    </Button>
                  </div>
                  <div className="mt-4 p-3 bg-slate-50 rounded-lg text-sm text-slate-600 flex items-center justify-between">
                    <div>
                      <strong>Automatische Backups:</strong>{' '}
                      {scheduleSettings ? (
                        <>
                          {getFrequencyLabel(scheduleSettings.backup_frequency)} um{' '}
                          {formatTimeString(scheduleSettings.database_backup_hour, scheduleSettings.database_backup_minute)} (Datenbank),{' '}
                          {formatTimeString(scheduleSettings.storage_backup_hour, scheduleSettings.storage_backup_minute)} (Storage).
                          Monatliche am 1. um {formatTimeString(scheduleSettings.monthly_backup_hour, scheduleSettings.monthly_backup_minute)}.
                        </>
                      ) : (
                        'Täglich um 02:00 Uhr (Datenbank), 02:30 Uhr (Storage).'
                      )}
                    </div>
                    <Button 
                      variant="outline" 
                      size="sm"
                      onClick={() => {
                        if (!scheduleSettings) fetchScheduleSettings();
                        setScheduleDialogOpen(true);
                      }}
                    >
                      <Clock className="h-4 w-4 mr-1" />
                      Zeitplan ändern
                    </Button>
                  </div>
                </CardContent>
              </Card>

              {/* Backups Table */}
              <Card>
                <CardHeader className="flex flex-row items-center justify-between">
                  <div>
                    <CardTitle>Alle Backups</CardTitle>
                    <CardDescription>
                      Aufbewahrung: Täglich {backupStatus?.retention_settings?.daily_retention_days || 30} Tage, 
                      Monatlich {backupStatus?.retention_settings?.monthly_retention_months || 12} Monate
                    </CardDescription>
                  </div>
                  <Button variant="outline" onClick={() => { fetchBackups(); fetchBackupStatus(); }}>
                    <RefreshCw className="h-4 w-4 mr-2" />
                    Aktualisieren
                  </Button>
                </CardHeader>
                <CardContent>
                  {backupsLoading ? (
                    <div className="flex justify-center py-8">
                      <Loader2 className="h-8 w-8 animate-spin text-slate-400" />
                    </div>
                  ) : backups.length === 0 ? (
                    <div className="text-center py-8 text-slate-500">
                      Noch keine Backups vorhanden
                    </div>
                  ) : (
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="border-b text-left">
                            <th className="py-3 px-2 font-semibold">Typ</th>
                            <th className="py-3 px-2 font-semibold">Dateiname</th>
                            <th className="py-3 px-2 font-semibold">Klasse</th>
                            <th className="py-3 px-2 font-semibold">Größe</th>
                            <th className="py-3 px-2 font-semibold">Status</th>
                            <th className="py-3 px-2 font-semibold">Cloud</th>
                            <th className="py-3 px-2 font-semibold">Erstellt am</th>
                            <th className="py-3 px-2 font-semibold">Aktionen</th>
                          </tr>
                        </thead>
                        <tbody>
                          {backups.map((backup) => (
                            <tr key={backup.id} className="border-b hover:bg-slate-50">
                              <td className="py-3 px-2">
                                <Badge variant={backup.backup_type === 'database' ? 'default' : 'secondary'}>
                                  {backup.backup_type === 'database' ? 'Datenbank' : 'Storage'}
                                </Badge>
                              </td>
                              <td className="py-3 px-2 font-mono text-xs">{backup.file_name}</td>
                              <td className="py-3 px-2">
                                <Badge variant="outline">
                                  {backup.retention_class === 'daily' ? 'Täglich' : 'Monatlich'}
                                </Badge>
                              </td>
                              <td className="py-3 px-2">{formatBytes(backup.file_size_bytes)}</td>
                              <td className="py-3 px-2">
                                {backup.status === 'success' ? (
                                  <Badge className="bg-green-100 text-green-800">Erfolgreich</Badge>
                                ) : backup.status === 'running' ? (
                                  <Badge className="bg-blue-100 text-blue-800">Läuft</Badge>
                                ) : (
                                  <Badge className="bg-red-100 text-red-800">Fehlgeschlagen</Badge>
                                )}
                              </td>
                              <td className="py-3 px-2">
                                {backup.supabase_uploaded ? (
                                  <Badge className="bg-green-100 text-green-800">
                                    <CloudDownload className="h-3 w-3 mr-1" />
                                    Ja
                                  </Badge>
                                ) : (
                                  <Badge variant="outline" className="text-slate-400">Nein</Badge>
                                )}
                              </td>
                              <td className="py-3 px-2">{formatDate(backup.created_at)}</td>
                              <td className="py-3 px-2">
                                <DropdownMenu>
                                  <DropdownMenuTrigger asChild>
                                    <Button variant="ghost" size="sm">
                                      <MoreVertical className="h-4 w-4" />
                                    </Button>
                                  </DropdownMenuTrigger>
                                  <DropdownMenuContent align="end">
                                    <DropdownMenuItem 
                                      onClick={() => handleDownloadBackup(backup.id, backup.file_name)}
                                      disabled={backup.status !== 'success'}
                                    >
                                      <CloudDownload className="h-4 w-4 mr-2" />
                                      Herunterladen
                                    </DropdownMenuItem>
                                    <DropdownMenuItem 
                                      onClick={() => handleVerifySingleBackup(backup.id)}
                                      disabled={backup.status !== 'success'}
                                    >
                                      <Shield className="h-4 w-4 mr-2" />
                                      Integrität prüfen
                                    </DropdownMenuItem>
                                    <DropdownMenuItem 
                                      onClick={() => {
                                        setSelectedBackup(backup);
                                        setRestoreDialogOpen(true);
                                      }}
                                      disabled={backup.status !== 'success'}
                                    >
                                      <RefreshCw className="h-4 w-4 mr-2" />
                                      Wiederherstellen
                                    </DropdownMenuItem>
                                    <DropdownMenuSeparator />
                                    <DropdownMenuItem 
                                      onClick={() => {
                                        setSelectedBackup(backup);
                                        setDeleteBackupDialogOpen(true);
                                      }}
                                      className="text-red-600"
                                    >
                                      <Trash2 className="h-4 w-4 mr-2" />
                                      Löschen
                                    </DropdownMenuItem>
                                  </DropdownMenuContent>
                                </DropdownMenu>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* Cloud Backups Section */}
              <Card>
                <CardHeader className="flex flex-row items-center justify-between">
                  <div>
                    <CardTitle className="flex items-center gap-2">
                      <CloudDownload className="h-5 w-5 text-blue-600" />
                      Cloud-Backups (Supabase)
                    </CardTitle>
                    <CardDescription>
                      Backups in der Cloud - für Notfall-Wiederherstellung wenn Server-Daten verloren
                    </CardDescription>
                  </div>
                  <div className="flex gap-2">
                    <Button 
                      variant="outline" 
                      onClick={() => {
                        setShowCloudBackups(!showCloudBackups);
                        if (!showCloudBackups && cloudBackups.length === 0) {
                          fetchCloudBackups();
                        }
                      }}
                    >
                      {showCloudBackups ? 'Ausblenden' : 'Cloud-Backups anzeigen'}
                    </Button>
                  </div>
                </CardHeader>
                
                {showCloudBackups && (
                  <CardContent>
                    {cloudBackupsLoading ? (
                      <div className="flex justify-center py-8">
                        <Loader2 className="h-8 w-8 animate-spin text-slate-400" />
                      </div>
                    ) : cloudBackups.length === 0 ? (
                      <div className="text-center py-8 text-slate-500">
                        <CloudDownload className="h-12 w-12 mx-auto mb-2 text-slate-300" />
                        <p>Keine Cloud-Backups gefunden</p>
                        <Button variant="outline" className="mt-4" onClick={fetchCloudBackups}>
                          <RefreshCw className="h-4 w-4 mr-2" />
                          Erneut prüfen
                        </Button>
                      </div>
                    ) : (
                      <div className="space-y-4">
                        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-sm text-blue-800">
                          <strong>Notfall-Wiederherstellung:</strong> Falls Ihre lokalen Daten verloren gegangen sind, 
                          können Sie hier ein Backup direkt aus der Supabase Cloud wiederherstellen.
                        </div>
                        
                        <div className="overflow-x-auto">
                          <table className="w-full text-sm">
                            <thead>
                              <tr className="border-b text-left">
                                <th className="py-3 px-2 font-semibold">Typ</th>
                                <th className="py-3 px-2 font-semibold">Dateiname</th>
                                <th className="py-3 px-2 font-semibold">Klasse</th>
                                <th className="py-3 px-2 font-semibold">Lokal</th>
                                <th className="py-3 px-2 font-semibold">Erstellt</th>
                                <th className="py-3 px-2 font-semibold">Aktion</th>
                              </tr>
                            </thead>
                            <tbody>
                              {cloudBackups.map((backup, index) => (
                                <tr key={index} className="border-b hover:bg-slate-50">
                                  <td className="py-3 px-2">
                                    <Badge variant={backup.backup_type === 'database' ? 'default' : 'secondary'}>
                                      {backup.backup_type === 'database' ? 'Datenbank' : 'Storage'}
                                    </Badge>
                                  </td>
                                  <td className="py-3 px-2 font-mono text-xs">{backup.name}</td>
                                  <td className="py-3 px-2">
                                    <Badge variant="outline">
                                      {backup.retention_class === 'daily' ? 'Täglich' : 'Monatlich'}
                                    </Badge>
                                  </td>
                                  <td className="py-3 px-2">
                                    {backup.local_available ? (
                                      <Badge className="bg-green-100 text-green-800">Vorhanden</Badge>
                                    ) : (
                                      <Badge className="bg-amber-100 text-amber-800">Nur Cloud</Badge>
                                    )}
                                  </td>
                                  <td className="py-3 px-2">{formatDate(backup.created_at)}</td>
                                  <td className="py-3 px-2">
                                    <Button 
                                      size="sm" 
                                      variant="outline"
                                      className="text-blue-600 border-blue-300 hover:bg-blue-50"
                                      onClick={() => {
                                        setSelectedCloudBackup(backup);
                                        setCloudRestoreDialogOpen(true);
                                      }}
                                    >
                                      <RefreshCw className="h-4 w-4 mr-1" />
                                      Von Cloud wiederherstellen
                                    </Button>
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                        
                        <div className="flex justify-end">
                          <Button variant="outline" size="sm" onClick={fetchCloudBackups}>
                            <RefreshCw className="h-4 w-4 mr-2" />
                            Liste aktualisieren
                          </Button>
                        </div>
                      </div>
                    )}
                  </CardContent>
                )}
              </Card>

              {/* System Status */}
              {backupStatus?.last_error && (
                <Card className="border-red-200 bg-red-50">
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2 text-red-700">
                      <AlertCircle className="h-5 w-5" />
                      Letzter Fehler
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm text-red-600">
                      {formatDate(backupStatus.last_error.date)}: {backupStatus.last_error.message}
                    </p>
                  </CardContent>
                </Card>
              )}
            </div>
          </TabsContent>

          {/* Profile Tab */}
          <TabsContent value="profile">
            <TwoFactorSetup />
          </TabsContent>
        </Tabs>
      </main>

      {/* Approval Dialog */}
      <Dialog open={approvalDialogOpen} onOpenChange={(open) => {
        setApprovalDialogOpen(open);
        if (!open) {
          setRejectionReason('');
        }
      }}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Abschleppdienst prüfen</DialogTitle>
            <DialogDescription>
              Prüfen Sie die Registrierungsdaten und den Gewerbenachweis
            </DialogDescription>
          </DialogHeader>

          {selectedService ? (
            <div className="space-y-6 py-4">
              <div className="grid sm:grid-cols-2 gap-4">
                <div>
                  <Label className="text-slate-500">Unternehmensname</Label>
                  <p className="font-bold text-lg">{selectedService.company_name}</p>
                </div>
                <div>
                  <Label className="text-slate-500">Ansprechpartner</Label>
                  <p className="font-medium">{selectedService.name}</p>
                </div>
                <div>
                  <Label className="text-slate-500">E-Mail</Label>
                  <p className="font-medium">{selectedService.email}</p>
                </div>
                <div>
                  <Label className="text-slate-500">Telefon</Label>
                  <p className="font-medium">{selectedService.phone}</p>
                </div>
                <div>
                  <Label className="text-slate-500">Geschäftsadresse</Label>
                  <p className="font-medium">{selectedService.address || '-'}</p>
                </div>
                <div>
                  <Label className="text-slate-500">Hof-Adresse</Label>
                  <p className="font-medium">{selectedService.yard_address}</p>
                </div>
                <div>
                  <Label className="text-slate-500">Öffnungszeiten</Label>
                  <p className="font-medium">{selectedService.opening_hours}</p>
                </div>
                <div>
                  <Label className="text-slate-500">Preise</Label>
                  <p className="font-medium">
                    Anfahrt: {selectedService.tow_cost?.toFixed(2) || '0.00'} € |
                    Standkosten: {selectedService.daily_cost?.toFixed(2) || '0.00'} €/Tag
                  </p>
                </div>
              </div>

              <div>
                <Label className="text-slate-500 mb-2 block">Gewerbenachweis</Label>
                {selectedService.business_license ? (
                  <div className="border rounded-lg p-4 bg-slate-50">
                    {selectedService.business_license.startsWith('data:image') ? (
                      <img
                        src={selectedService.business_license}
                        alt="Gewerbenachweis"
                        className="max-w-full max-h-96 mx-auto rounded"
                      />
                    ) : selectedService.business_license.startsWith('data:application/pdf') ? (
                      <div className="text-center">
                        <FileText className="h-16 w-16 text-slate-400 mx-auto mb-2" />
                        <p className="text-sm text-slate-600">PDF-Dokument</p>
                        <a
                          href={selectedService.business_license}
                          download="gewerbenachweis.pdf"
                          className="text-orange-600 hover:text-orange-700 text-sm font-medium"
                        >
                          Herunterladen
                        </a>
                      </div>
                    ) : (
                      <p className="text-sm text-slate-500">Dokument nicht verfügbar</p>
                    )}
                  </div>
                ) : (
                  <p className="text-sm text-red-600">Kein Gewerbenachweis hochgeladen</p>
                )}
              </div>

              <div>
                <Label htmlFor="rejectionReason">Ablehnungsgrund (optional)</Label>
                <Textarea
                  id="rejectionReason"
                  value={rejectionReason}
                  onChange={(e) => setRejectionReason(e.target.value)}
                  placeholder="Falls Sie ablehnen: Grund für die Ablehnung..."
                  rows={2}
                  className="mt-1"
                />
              </div>

              <div className="flex gap-3">
                <Button
                  data-testid="reject-service-btn"
                  variant="destructive"
                  onClick={() => handleApproval(false)}
                  disabled={approving}
                  className="flex-1"
                >
                  <X className="h-4 w-4 mr-2" />
                  Ablehnen
                </Button>
                <Button
                  data-testid="approve-service-btn"
                  onClick={() => handleApproval(true)}
                  disabled={approving}
                  className="flex-1 bg-green-600 hover:bg-green-700"
                >
                  <CheckCircle className="h-4 w-4 mr-2" />
                  Freischalten
                </Button>
              </div>
            </div>
          ) : (
            <div className="py-8 text-center text-slate-500">
              <p>Laden...</p>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Password Change Dialog */}
      <Dialog open={passwordDialogOpen} onOpenChange={setPasswordDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Key className="h-5 w-5" />
              Passwort ändern
            </DialogTitle>
            <DialogDescription>
              Neues Passwort für {selectedUser?.name} setzen
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="newPassword">Neues Passwort</Label>
              <Input
                data-testid="new-password-input"
                id="newPassword"
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                placeholder="Mindestens 6 Zeichen"
                minLength={6}
              />
            </div>

            <Button
              data-testid="save-password-btn"
              onClick={handleUpdatePassword}
              disabled={actionLoading || newPassword.length < 8}
              className="w-full bg-slate-900 hover:bg-slate-800"
            >
              {actionLoading ? <div className="loading-spinner mr-2"></div> : <Key className="h-4 w-4 mr-2" />}
              Passwort speichern
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle className="flex items-center gap-2 text-red-600">
              <Trash2 className="h-5 w-5" />
              Benutzer löschen
            </AlertDialogTitle>
            <AlertDialogDescription>
              Sind Sie sicher, dass Sie <strong>{selectedUser?.name}</strong> ({selectedUser?.email})
              permanent löschen möchten? Diese Aktion kann nicht rückgängig gemacht werden.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Abbrechen</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDeleteUser}
              className="bg-red-600 hover:bg-red-700"
              disabled={actionLoading}
            >
              {actionLoading ? <div className="loading-spinner mr-2"></div> : <Trash2 className="h-4 w-4 mr-2" />}
              Endgültig löschen
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Authority Approval Dialog */}
      <Dialog open={authorityApprovalDialogOpen} onOpenChange={setAuthorityApprovalDialogOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Shield className="h-5 w-5 text-blue-500" />
              Behörde prüfen
            </DialogTitle>
            <DialogDescription>
              Prüfen Sie die Registrierungsanfrage und entscheiden Sie über die Freischaltung
            </DialogDescription>
          </DialogHeader>

          {selectedAuthority && (
            <div className="space-y-4">
              <div className="p-4 bg-blue-50 rounded-lg">
                <h3 className="font-bold text-lg">{selectedAuthority.authority_name}</h3>
                <p className="text-sm text-slate-500">{selectedAuthority.email}</p>
              </div>

              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <p className="text-slate-500">Ansprechpartner</p>
                  <p className="font-medium">{selectedAuthority.name}</p>
                </div>
                <div>
                  <p className="text-slate-500">Abteilung</p>
                  <p className="font-medium">{selectedAuthority.department || '-'}</p>
                </div>
                <div>
                  <p className="text-slate-500">Dienstnummer</p>
                  <p className="font-mono font-medium">{selectedAuthority.dienstnummer}</p>
                </div>
                <div>
                  <p className="text-slate-500">Registriert am</p>
                  <p className="font-medium">{new Date(selectedAuthority.created_at).toLocaleDateString('de-DE')}</p>
                </div>
              </div>

              <div className="space-y-2">
                <Label>Ablehnungsgrund (optional)</Label>
                <Textarea
                  value={rejectionReason}
                  onChange={(e) => setRejectionReason(e.target.value)}
                  placeholder="Grund für die Ablehnung eingeben..."
                  rows={3}
                />
              </div>

              <div className="flex gap-3">
                <Button
                  onClick={() => handleAuthorityApproval(false)}
                  disabled={approving}
                  variant="outline"
                  className="flex-1 text-red-600 border-red-200 hover:bg-red-50"
                >
                  <X className="h-4 w-4 mr-2" />
                  Ablehnen
                </Button>
                <Button
                  onClick={() => handleAuthorityApproval(true)}
                  disabled={approving}
                  className="flex-1 bg-green-600 hover:bg-green-700"
                >
                  <CheckCircle className="h-4 w-4 mr-2" />
                  Freischalten
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Restore Backup Confirmation Dialog */}
      <AlertDialog open={restoreDialogOpen} onOpenChange={setRestoreDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle className="flex items-center gap-2 text-amber-600">
              <RefreshCw className="h-5 w-5" />
              Backup wiederherstellen
            </AlertDialogTitle>
            <AlertDialogDescription className="space-y-2">
              <p>
                <strong className="text-red-600">Warnung:</strong> Diese Aktion kann bestehende Daten überschreiben!
              </p>
              <p>
                Möchten Sie wirklich das Backup <strong>{selectedBackup?.file_name}</strong> vom{' '}
                <strong>{formatDate(selectedBackup?.created_at)}</strong> wiederherstellen?
              </p>
              <p className="text-sm text-slate-500 mt-2">
                {selectedBackup?.backup_type === 'database' 
                  ? 'Die gesamte Datenbank wird auf den Stand dieses Backups zurückgesetzt.'
                  : 'Alle gespeicherten Dateien werden aus diesem Backup wiederhergestellt.'}
              </p>
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => setSelectedBackup(null)}>Abbrechen</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleRestoreBackup}
              className="bg-amber-600 hover:bg-amber-700"
              disabled={actionLoading}
            >
              {actionLoading ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <RefreshCw className="h-4 w-4 mr-2" />}
              Ja, wiederherstellen
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Delete Backup Confirmation Dialog */}
      <AlertDialog open={deleteBackupDialogOpen} onOpenChange={setDeleteBackupDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle className="flex items-center gap-2 text-red-600">
              <Trash2 className="h-5 w-5" />
              Backup löschen
            </AlertDialogTitle>
            <AlertDialogDescription>
              Sind Sie sicher, dass Sie das Backup <strong>{selectedBackup?.file_name}</strong> löschen möchten?
              Diese Aktion kann nicht rückgängig gemacht werden.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => setSelectedBackup(null)}>Abbrechen</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDeleteBackup}
              className="bg-red-600 hover:bg-red-700"
              disabled={actionLoading}
            >
              {actionLoading ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Trash2 className="h-4 w-4 mr-2" />}
              Endgültig löschen
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Cloud Restore Confirmation Dialog */}
      <AlertDialog open={cloudRestoreDialogOpen} onOpenChange={setCloudRestoreDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle className="flex items-center gap-2 text-blue-600">
              <CloudDownload className="h-5 w-5" />
              Von Cloud wiederherstellen
            </AlertDialogTitle>
            <AlertDialogDescription className="space-y-3">
              <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 text-amber-800">
                <strong>⚠️ Warnung:</strong> Diese Aktion lädt das Backup von Supabase Cloud und überschreibt bestehende Daten!
              </div>
              <p>
                Möchten Sie wirklich das Cloud-Backup <strong>{selectedCloudBackup?.name}</strong> wiederherstellen?
              </p>
              <p className="text-sm text-slate-500">
                Pfad: {selectedCloudBackup?.path}
              </p>
              {selectedCloudBackup?.local_available && (
                <p className="text-sm text-green-600">
                  ✓ Dieses Backup ist auch lokal verfügbar. Sie können stattdessen das lokale Backup verwenden.
                </p>
              )}
              {!selectedCloudBackup?.local_available && (
                <p className="text-sm text-amber-600">
                  ⚠ Dieses Backup existiert NUR in der Cloud und nicht mehr lokal.
                </p>
              )}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => setSelectedCloudBackup(null)}>Abbrechen</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleRestoreFromCloud}
              className="bg-blue-600 hover:bg-blue-700"
              disabled={actionLoading}
            >
              {actionLoading ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <CloudDownload className="h-4 w-4 mr-2" />}
              Ja, von Cloud wiederherstellen
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Schedule Settings Dialog */}
      <Dialog open={scheduleDialogOpen} onOpenChange={setScheduleDialogOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Clock className="h-5 w-5" />
              Backup-Zeitplan konfigurieren
            </DialogTitle>
            <DialogDescription>
              Passen Sie an, wann automatische Backups erstellt werden sollen.
            </DialogDescription>
          </DialogHeader>
          
          {scheduleSettings && (
            <div className="space-y-6 py-4">
              {/* Backup Frequency */}
              <div className="space-y-2">
                <label className="text-sm font-medium">Backup-Häufigkeit</label>
                <select
                  className="w-full p-2 border rounded-lg"
                  value={scheduleSettings.backup_frequency}
                  onChange={(e) => setScheduleSettings({...scheduleSettings, backup_frequency: e.target.value})}
                >
                  <option value="daily">Täglich</option>
                  <option value="every_12h">Alle 12 Stunden</option>
                  <option value="every_6h">Alle 6 Stunden</option>
                </select>
              </div>

              {/* Database Backup Time */}
              <div className="space-y-2">
                <label className="text-sm font-medium">Datenbank-Backup Uhrzeit (UTC)</label>
                <div className="flex gap-2">
                  <input
                    type="number"
                    min="0"
                    max="23"
                    className="w-20 p-2 border rounded-lg text-center"
                    value={scheduleSettings.database_backup_hour}
                    onChange={(e) => setScheduleSettings({...scheduleSettings, database_backup_hour: parseInt(e.target.value) || 0})}
                  />
                  <span className="self-center">:</span>
                  <input
                    type="number"
                    min="0"
                    max="59"
                    className="w-20 p-2 border rounded-lg text-center"
                    value={scheduleSettings.database_backup_minute}
                    onChange={(e) => setScheduleSettings({...scheduleSettings, database_backup_minute: parseInt(e.target.value) || 0})}
                  />
                  <span className="self-center text-sm text-slate-500">Uhr</span>
                </div>
              </div>

              {/* Storage Backup Time */}
              <div className="space-y-2">
                <label className="text-sm font-medium">Storage-Backup Uhrzeit (UTC)</label>
                <div className="flex gap-2">
                  <input
                    type="number"
                    min="0"
                    max="23"
                    className="w-20 p-2 border rounded-lg text-center"
                    value={scheduleSettings.storage_backup_hour}
                    onChange={(e) => setScheduleSettings({...scheduleSettings, storage_backup_hour: parseInt(e.target.value) || 0})}
                  />
                  <span className="self-center">:</span>
                  <input
                    type="number"
                    min="0"
                    max="59"
                    className="w-20 p-2 border rounded-lg text-center"
                    value={scheduleSettings.storage_backup_minute}
                    onChange={(e) => setScheduleSettings({...scheduleSettings, storage_backup_minute: parseInt(e.target.value) || 0})}
                  />
                  <span className="self-center text-sm text-slate-500">Uhr</span>
                </div>
              </div>

              {/* Monthly Backup Time */}
              <div className="space-y-2">
                <label className="text-sm font-medium">Monatliches Backup Uhrzeit (UTC) - am 1. jeden Monats</label>
                <div className="flex gap-2">
                  <input
                    type="number"
                    min="0"
                    max="23"
                    className="w-20 p-2 border rounded-lg text-center"
                    value={scheduleSettings.monthly_backup_hour}
                    onChange={(e) => setScheduleSettings({...scheduleSettings, monthly_backup_hour: parseInt(e.target.value) || 0})}
                  />
                  <span className="self-center">:</span>
                  <input
                    type="number"
                    min="0"
                    max="59"
                    className="w-20 p-2 border rounded-lg text-center"
                    value={scheduleSettings.monthly_backup_minute}
                    onChange={(e) => setScheduleSettings({...scheduleSettings, monthly_backup_minute: parseInt(e.target.value) || 0})}
                  />
                  <span className="self-center text-sm text-slate-500">Uhr</span>
                </div>
              </div>

              {/* Retention Settings */}
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium">Tägliche Backups aufbewahren</label>
                  <div className="flex items-center gap-2">
                    <input
                      type="number"
                      min="1"
                      max="365"
                      className="w-20 p-2 border rounded-lg text-center"
                      value={scheduleSettings.retention_days}
                      onChange={(e) => setScheduleSettings({...scheduleSettings, retention_days: parseInt(e.target.value) || 30})}
                    />
                    <span className="text-sm text-slate-500">Tage</span>
                  </div>
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">Monatliche Backups aufbewahren</label>
                  <div className="flex items-center gap-2">
                    <input
                      type="number"
                      min="1"
                      max="120"
                      className="w-20 p-2 border rounded-lg text-center"
                      value={scheduleSettings.retention_months}
                      onChange={(e) => setScheduleSettings({...scheduleSettings, retention_months: parseInt(e.target.value) || 12})}
                    />
                    <span className="text-sm text-slate-500">Monate</span>
                  </div>
                </div>
              </div>

              <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 text-sm text-amber-800">
                <strong>Hinweis:</strong> Änderungen werden sofort gespeichert, aber der Backup-Scheduler 
                wird erst beim nächsten Server-Neustart aktualisiert.
              </div>
            </div>
          )}

          <DialogFooter>
            <Button variant="outline" onClick={() => setScheduleDialogOpen(false)}>
              Abbrechen
            </Button>
            <Button onClick={handleSaveSchedule} disabled={savingSchedule}>
              {savingSchedule ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <CheckCircle className="h-4 w-4 mr-2" />}
              Speichern
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default AdminDashboard;
