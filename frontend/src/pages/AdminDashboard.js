import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import axios from 'axios';
import { 
  Car, Search, LogOut, Users, Truck, Shield, Building2, 
  CheckCircle, Clock, Download, Filter, BarChart3, AlertCircle,
  FileText, X, Eye
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { Badge } from '../components/ui/badge';
import { toast } from 'sonner';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export const AdminDashboard = () => {
  const { user, logout } = useAuth();
  const [activeTab, setActiveTab] = useState('overview');
  const [stats, setStats] = useState(null);
  const [jobs, setJobs] = useState([]);
  const [users, setUsers] = useState([]);
  const [pendingServices, setPendingServices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  
  // Approval dialog state
  const [selectedService, setSelectedService] = useState(null);
  const [approvalDialogOpen, setApprovalDialogOpen] = useState(false);
  const [rejectionReason, setRejectionReason] = useState('');
  const [approving, setApproving] = useState(false);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [statsRes, jobsRes, usersRes, pendingRes] = await Promise.all([
        axios.get(`${API}/admin/stats`),
        axios.get(`${API}/admin/jobs`),
        axios.get(`${API}/admin/users`),
        axios.get(`${API}/admin/pending-services`)
      ]);
      setStats(statsRes.data);
      setJobs(jobsRes.data);
      setUsers(usersRes.data);
      setPendingServices(pendingRes.data);
    } catch (error) {
      console.error('Error fetching data:', error);
      toast.error('Fehler beim Laden der Daten');
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = async () => {
    try {
      const params = new URLSearchParams();
      if (searchQuery) params.append('search', searchQuery);
      if (statusFilter && statusFilter !== 'all') params.append('status', statusFilter);
      
      const response = await axios.get(`${API}/admin/jobs?${params.toString()}`);
      setJobs(response.data);
    } catch (error) {
      toast.error('Fehler bei der Suche');
    }
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

  const openApprovalDialog = (service) => {
    setSelectedService(service);
    setApprovalDialogOpen(true);
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
      admin: { label: 'Admin', icon: Shield, class: 'bg-purple-100 text-purple-700' },
      authority: { label: 'Behörde', icon: Shield, class: 'bg-blue-100 text-blue-700' },
      towing_service: { label: 'Abschleppdienst', icon: Truck, class: 'bg-orange-100 text-orange-700' }
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

  const downloadPDF = (jobId) => {
    window.open(`${API}/jobs/${jobId}/pdf`, '_blank');
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
              {/* Pending Approvals Badge */}
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
              {stats?.pending_approvals > 0 && (
                <span className="absolute -top-1 -right-1 bg-red-500 text-white text-xs w-5 h-5 rounded-full flex items-center justify-center">
                  {stats.pending_approvals}
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
          </TabsList>

          {/* Overview Tab */}
          <TabsContent value="overview">
            {loading ? (
              <div className="flex justify-center py-8">
                <div className="loading-spinner"></div>
              </div>
            ) : stats && (
              <>
                {/* Alert for pending approvals */}
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

                {/* Stats Grid */}
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

                {/* User Stats */}
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
                ) : pendingServices.length === 0 ? (
                  <div className="empty-state">
                    <CheckCircle className="empty-state-icon text-green-500" />
                    <p>Keine ausstehenden Freischaltungen</p>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {pendingServices.map(service => (
                      <div 
                        key={service.id} 
                        className="border rounded-lg p-4 hover:shadow-md transition-shadow"
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
                              <div>
                                <p className="text-slate-500">Anfahrtskosten</p>
                                <p className="font-medium">{service.tow_cost?.toFixed(2) || '0.00'} €</p>
                              </div>
                              <div>
                                <p className="text-slate-500">Standkosten/Tag</p>
                                <p className="font-medium">{service.daily_cost?.toFixed(2) || '0.00'} €</p>
                              </div>
                            </div>
                            <div>
                              <p className="text-slate-500 text-sm">Registriert am</p>
                              <p className="font-medium text-sm">{new Date(service.created_at).toLocaleString('de-DE')}</p>
                            </div>
                          </div>
                          <Button 
                            onClick={() => openApprovalDialog(service)}
                            className="bg-slate-900 hover:bg-slate-800"
                          >
                            <Eye className="h-4 w-4 mr-2" />
                            Prüfen
                          </Button>
                        </div>
                      </div>
                    ))}
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
                          <th>Abschleppdienst</th>
                          <th>Erstellt</th>
                          <th>Aktionen</th>
                        </tr>
                      </thead>
                      <tbody>
                        {jobs.map(job => (
                          <tr key={job.id}>
                            <td className="font-mono text-sm">{job.job_number}</td>
                            <td className="font-bold">{job.license_plate}</td>
                            <td>{getStatusBadge(job.status)}</td>
                            <td>{job.created_by_authority || job.created_by_name}</td>
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
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* Users Tab */}
          <TabsContent value="users">
            <Card>
              <CardHeader>
                <CardTitle>Registrierte Benutzer</CardTitle>
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
                        </tr>
                      </thead>
                      <tbody>
                        {users.map(u => (
                          <tr key={u.id}>
                            <td className="font-medium">{u.name}</td>
                            <td>{u.email}</td>
                            <td>{getRoleBadge(u.role)}</td>
                            <td>
                              {u.authority_name || u.company_name || '-'}
                            </td>
                            <td>
                              {u.role === 'towing_service' ? getApprovalBadge(u.approval_status) : '-'}
                            </td>
                            <td>{new Date(u.created_at).toLocaleDateString('de-DE')}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </main>

      {/* Approval Dialog */}
      <Dialog open={approvalDialogOpen} onOpenChange={setApprovalDialogOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Abschleppdienst prüfen</DialogTitle>
            <DialogDescription>
              Prüfen Sie die Registrierungsdaten und den Gewerbenachweis
            </DialogDescription>
          </DialogHeader>

          {selectedService && (
            <div className="space-y-6 py-4">
              {/* Company Info */}
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

              {/* Business License */}
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

              {/* Rejection Reason */}
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

              {/* Action Buttons */}
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
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default AdminDashboard;
