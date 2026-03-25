import React, { useState, useEffect, useRef } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useDeltaPolling } from '../hooks/useDeltaPolling';
import axios from 'axios';
import {
  Car, MapPin, Camera, Plus, LogOut, FileText, Menu, X,
  Search, Clock, ChevronRight, Trash2, Link as LinkIcon, CheckCircle,
  Users, UserPlus, Lock, Unlock, Key, Badge, Download, Filter, Calendar, Settings,
  User, Euro, Building2
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { MapContainer, TileLayer, Marker, useMapEvents } from 'react-leaflet';
import { toast } from 'sonner';
import { Pagination } from '../components/Pagination';
import TwoFactorSetup from '../components/profile/TwoFactorSetup';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';

// Fix Leaflet default marker icon
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
});

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// Image compression utility function
const compressImage = (file, maxWidth = 1200, quality = 0.7) => {
  return new Promise((resolve) => {
    const reader = new FileReader();
    reader.onload = (event) => {
      const img = new window.Image();
      img.onload = () => {
        const canvas = document.createElement('canvas');
        let width = img.width;
        let height = img.height;

        if (width > maxWidth) {
          height = Math.round((height * maxWidth) / width);
          width = maxWidth;
        }

        canvas.width = width;
        canvas.height = height;

        const ctx = canvas.getContext('2d');
        ctx.drawImage(img, 0, 0, width, height);

        const compressedDataUrl = canvas.toDataURL('image/jpeg', quality);
        resolve(compressedDataUrl);
      };
      img.src = event.target.result;
    };
    reader.readAsDataURL(file);
  });
};

// Location Picker Component
const LocationPicker = ({ position, setPosition }) => {
  useMapEvents({
    click(e) {
      setPosition([e.latlng.lat, e.latlng.lng]);
    },
  });

  return position ? <Marker position={position} /> : null;
};

export const AuthorityDashboard = () => {
  const { user, logout } = useAuth();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [activeTab, setActiveTab] = useState('new');
  const [initialJobs, setInitialJobs] = useState([]);
  const { jobs, setJobs } = useDeltaPolling(initialJobs, user?.role);
  const [linkedServices, setLinkedServices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [serviceCodeInput, setServiceCodeInput] = useState('');
  const [linkDialogOpen, setLinkDialogOpen] = useState(false);

  // Pagination state
  const [currentPage, setCurrentPage] = useState(1);
  const [totalJobs, setTotalJobs] = useState(0);
  const itemsPerPage = 50;

  // NEW: Filter state
  const [filterOpen, setFilterOpen] = useState(false);
  const [filterStatus, setFilterStatus] = useState('all');
  const [filterDateFrom, setFilterDateFrom] = useState('');
  const [filterDateTo, setFilterDateTo] = useState('');
  const [filterService, setFilterService] = useState('all');

  // Employee management state
  const [employees, setEmployees] = useState([]);
  const [employeeDialogOpen, setEmployeeDialogOpen] = useState(false);
  const [newEmployeeName, setNewEmployeeName] = useState('');
  const [newEmployeeEmail, setNewEmployeeEmail] = useState('');
  const [newEmployeePassword, setNewEmployeePassword] = useState('');
  const [creatingEmployee, setCreatingEmployee] = useState(false);
  const [passwordDialogOpen, setPasswordDialogOpen] = useState(false);
  const [selectedEmployee, setSelectedEmployee] = useState(null);
  const [newPassword, setNewPassword] = useState('');

  // New job form state
  const [licensePlate, setLicensePlate] = useState('');
  const [vin, setVin] = useState('');
  const [towReason, setTowReason] = useState('');
  const [locationAddress, setLocationAddress] = useState('');
  const [position, setPosition] = useState(null);
  const [photos, setPhotos] = useState([]);
  const [notes, setNotes] = useState('');
  const [selectedServiceId, setSelectedServiceId] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const fileInputRef = useRef(null);

  // NEW: Job type and Sicherstellung fields
  const [jobType, setJobType] = useState('towing');
  const [sicherstellungReason, setSicherstellungReason] = useState('');
  const [vehicleCategory, setVehicleCategory] = useState('');
  const [orderingAuthority, setOrderingAuthority] = useState('');
  const [contactAttempts, setContactAttempts] = useState(false);
  const [contactAttemptsNotes, setContactAttemptsNotes] = useState('');
  const [estimatedVehicleValue, setEstimatedVehicleValue] = useState('');

  // NEW: Weight categories from towing service
  const [serviceWeightCategories, setServiceWeightCategories] = useState([]);
  const [selectedWeightCategoryId, setSelectedWeightCategoryId] = useState('');
  const [selectedWeightCategory, setSelectedWeightCategory] = useState(null);

  // NEW: Authority settings (yard model & pricing)
  const [authoritySettings, setAuthoritySettings] = useState({
    yard_model: 'service_yard',
    price_categories: [],
    yards: [],  // Multiple yards
    yard_address: '',
    yard_lat: null,
    yard_lng: null
  });
  const [targetYard, setTargetYard] = useState('service_yard');
  const [selectedYardId, setSelectedYardId] = useState('');  // Selected yard when creating job
  const [selectedYard, setSelectedYard] = useState(null);
  const [selectedPriceCategoryId, setSelectedPriceCategoryId] = useState('');
  const [selectedPriceCategory, setSelectedPriceCategory] = useState(null);
  const [newPriceCategory, setNewPriceCategory] = useState({
    name: '',
    base_price: '',
    daily_rate: ''
  });
  const [newYard, setNewYard] = useState({
    name: '',
    address: '',
    phone: ''
  });
  const [savingSettings, setSavingSettings] = useState(false);

  // NEW: Authority Yard Release state
  const [releaseDialogOpen, setReleaseDialogOpen] = useState(false);
  const [selectedYardJob, setSelectedYardJob] = useState(null);
  const [releaseData, setReleaseData] = useState({
    owner_first_name: '',
    owner_last_name: '',
    owner_address: '',
    payment_method: 'bar',
    payment_amount: '',
    service_invoice_amount: ''
  });
  const [releasingJob, setReleasingJob] = useState(false);

  // NEW: Edit/Delete Job state
  const [editJobDialogOpen, setEditJobDialogOpen] = useState(false);
  const [editingJobData, setEditingJobData] = useState(false);
  const [selectedJobForEdit, setSelectedJobForEdit] = useState(null);
  const [vehicleCategoryDialogOpen, setVehicleCategoryDialogOpen] = useState(false);
  const [editJobData, setEditJobData] = useState({
    license_plate: '',
    vin: '',
    tow_reason: '',
    notes: '',
    location_address: '',
    location_lat: null,
    location_lng: null
  });
  const [editJobPosition, setEditJobPosition] = useState(null);
  const [deletingJob, setDeletingJob] = useState(null);

  useEffect(() => {
    fetchJobs();
    fetchLinkedServices();
    fetchAuthoritySettings();
    if (user?.is_main_authority) {
      fetchEmployees();
    }
  }, [user, currentPage, filterStatus, filterDateFrom, filterDateTo, filterService]);

  // Fetch authority settings
  const fetchAuthoritySettings = async () => {
    try {
      const response = await axios.get(`${API}/authority/settings`);
      setAuthoritySettings(response.data);
      setTargetYard(response.data.yard_model || 'service_yard');
    } catch (error) {
      console.error('Error fetching authority settings:', error);
    }
  };

  // Save authority settings
  const handleSaveAuthoritySettings = async () => {
    setSavingSettings(true);
    try {
      const response = await axios.patch(`${API}/authority/settings`, {
        yard_model: authoritySettings.yard_model,
        price_categories: authoritySettings.price_categories,
        yards: authoritySettings.yards,
        yard_address: authoritySettings.yard_address,
        yard_lat: authoritySettings.yard_lat,
        yard_lng: authoritySettings.yard_lng
      });
      toast.success('Einstellungen gespeichert!');
      fetchAuthoritySettings();
    } catch (error) {
      toast.error('Fehler beim Speichern');
    } finally {
      setSavingSettings(false);
    }
  };

  // Add price category
  const handleAddPriceCategory = () => {
    if (!newPriceCategory.name.trim() || !newPriceCategory.base_price) {
      toast.error('Name und Grundpreis sind erforderlich');
      return;
    }
    const newCat = {
      id: crypto.randomUUID(),
      name: newPriceCategory.name.trim(),
      base_price: parseFloat(newPriceCategory.base_price) || 0,
      daily_rate: parseFloat(newPriceCategory.daily_rate) || 0,
      is_active: true
    };
    setAuthoritySettings({
      ...authoritySettings,
      price_categories: [...(authoritySettings.price_categories || []), newCat]
    });
    setNewPriceCategory({ name: '', base_price: '', daily_rate: '' });
  };

  // Remove price category
  const handleRemovePriceCategory = (categoryId) => {
    setAuthoritySettings({
      ...authoritySettings,
      price_categories: (authoritySettings.price_categories || []).filter(cat => cat.id !== categoryId)
    });
  };

  // Add yard
  const handleAddYard = () => {
    if (!newYard.name.trim() || !newYard.address.trim()) {
      toast.error('Name und Adresse sind erforderlich');
      return;
    }
    const yard = {
      id: crypto.randomUUID(),
      name: newYard.name.trim(),
      address: newYard.address.trim(),
      phone: newYard.phone.trim() || null,
      lat: null,
      lng: null,
      is_active: true
    };
    setAuthoritySettings({
      ...authoritySettings,
      yards: [...(authoritySettings.yards || []), yard]
    });
    setNewYard({ name: '', address: '', phone: '' });
  };

  // Remove yard
  const handleRemoveYard = (yardId) => {
    setAuthoritySettings({
      ...authoritySettings,
      yards: (authoritySettings.yards || []).filter(y => y.id !== yardId)
    });
  };

  // Handle authority release (when vehicles are on authority yard)
  const handleAuthorityRelease = async () => {
    if (!selectedYardJob || !releaseData.owner_first_name || !releaseData.owner_last_name || !releaseData.payment_amount) {
      toast.error('Bitte füllen Sie alle Pflichtfelder aus');
      return;
    }

    setReleasingJob(true);
    try {
      await axios.post(`${API}/jobs/${selectedYardJob.id}/authority-release`, {
        owner_first_name: releaseData.owner_first_name,
        owner_last_name: releaseData.owner_last_name,
        owner_address: releaseData.owner_address,
        payment_method: releaseData.payment_method,
        payment_amount: parseFloat(releaseData.payment_amount),
        service_invoice_amount: releaseData.service_invoice_amount ? parseFloat(releaseData.service_invoice_amount) : null
      });

      toast.success('Fahrzeug erfolgreich freigegeben');
      setReleaseDialogOpen(false);
      setSelectedYardJob(null);
      setReleaseData({
        owner_first_name: '',
        owner_last_name: '',
        owner_address: '',
        payment_method: 'bar',
        payment_amount: '',
        service_invoice_amount: ''
      });
      fetchJobs();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Fehler bei der Freigabe');
    } finally {
      setReleasingJob(false);
    }
  };

  // Calculate authority costs for a job
  const calculateAuthorityCosts = (job) => {
    if (!job) return { total: 0, breakdown: [] };
    
    const basePrice = job.authority_base_price || 0;
    const dailyRate = job.authority_daily_rate || 0;
    
    // Calculate days
    let days = 1;
    if (job.delivered_to_authority_at) {
      const deliveredDate = new Date(job.delivered_to_authority_at);
      const now = new Date();
      days = Math.max(1, Math.ceil((now - deliveredDate) / (1000 * 60 * 60 * 24)));
    }
    
    const breakdown = [];
    let total = 0;
    
    if (basePrice > 0) {
      breakdown.push({ label: `${job.authority_price_category_name || 'Grundpreis'} (erste 24h)`, amount: basePrice });
      total += basePrice;
    }
    
    if (days > 1 && dailyRate > 0) {
      const additionalCost = (days - 1) * dailyRate;
      breakdown.push({ label: `${days - 1} × weitere 24h à ${dailyRate.toFixed(2)}€`, amount: additionalCost });
      total += additionalCost;
    }
    
    return { total, breakdown, days };
  };

  const fetchJobs = async () => {
    try {
      const params = new URLSearchParams();
      params.append('page', currentPage.toString());
      params.append('limit', itemsPerPage.toString());

      // Add filter params
      if (filterStatus && filterStatus !== 'all') {
        params.append('status', filterStatus);
      }
      if (filterDateFrom) {
        params.append('date_from', filterDateFrom);
      }
      if (filterDateTo) {
        params.append('date_to', filterDateTo);
      }
      if (filterService && filterService !== 'all') {
        params.append('service_id', filterService);
      }

      // Count params
      const countParams = new URLSearchParams();
      if (filterStatus && filterStatus !== 'all') {
        countParams.append('status', filterStatus);
      }
      if (filterDateFrom) {
        countParams.append('date_from', filterDateFrom);
      }
      if (filterDateTo) {
        countParams.append('date_to', filterDateTo);
      }
      if (filterService && filterService !== 'all') {
        countParams.append('service_id', filterService);
      }

      const [jobsRes, countRes] = await Promise.all([
        axios.get(`${API}/jobs?${params.toString()}`),
        axios.get(`${API}/jobs/count/total${countParams.toString() ? '?' + countParams.toString() : ''}`)
      ]);
      setInitialJobs(jobsRes.data);
      setTotalJobs(countRes.data.total);
    } catch (error) {
      console.error('Error fetching jobs:', error);
    } finally {
      setLoading(false);
    }
  };

  // NEW: Check if filters are active
  const hasActiveFilters = filterStatus !== 'all' || filterDateFrom || filterDateTo || filterService !== 'all';

  // NEW: Clear all filters
  const clearFilters = () => {
    setFilterStatus('all');
    setFilterDateFrom('');
    setFilterDateTo('');
    setFilterService('all');
    setCurrentPage(1);
  };

  const handlePageChange = (page) => {
    setCurrentPage(page);
  };

  const fetchEmployees = async () => {
    try {
      const response = await axios.get(`${API}/authority/employees`);
      setEmployees(response.data);
    } catch (error) {
      console.error('Error fetching employees:', error);
    }
  };

  const fetchLinkedServices = async () => {
    try {
      const response = await axios.get(`${API}/services`);
      setLinkedServices(response.data);
    } catch (error) {
      console.error('Error fetching services:', error);
    }
  };

  // NEW: Fetch weight categories when a service is selected
  const fetchServiceWeightCategories = async (serviceId) => {
    if (!serviceId) {
      setServiceWeightCategories([]);
      return;
    }
    try {
      const response = await axios.get(`${API}/services/${serviceId}/weight-categories`);
      setServiceWeightCategories(response.data.weight_categories || []);
    } catch (error) {
      console.error('Error fetching weight categories:', error);
      setServiceWeightCategories([]);
    }
  };

  // Employee Management Functions
  const handleCreateEmployee = async (e) => {
    e.preventDefault();
    if (!newEmployeeName || !newEmployeeEmail || !newEmployeePassword) {
      toast.error('Bitte füllen Sie alle Felder aus');
      return;
    }

    setCreatingEmployee(true);
    try {
      await axios.post(`${API}/authority/employees`, {
        name: newEmployeeName,
        email: newEmployeeEmail,
        password: newEmployeePassword
      });
      toast.success('Mitarbeiter erfolgreich angelegt');
      setEmployeeDialogOpen(false);
      setNewEmployeeName('');
      setNewEmployeeEmail('');
      setNewEmployeePassword('');
      fetchEmployees();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Fehler beim Anlegen');
    } finally {
      setCreatingEmployee(false);
    }
  };

  const handleBlockEmployee = async (employeeId, block) => {
    try {
      await axios.patch(`${API}/authority/employees/${employeeId}/block`, { blocked: block });
      toast.success(block ? 'Mitarbeiter gesperrt' : 'Mitarbeiter entsperrt');
      fetchEmployees();
    } catch (error) {
      toast.error('Fehler beim Aktualisieren');
    }
  };

  const handleDeleteEmployee = async (employeeId) => {
    if (!window.confirm('Mitarbeiter wirklich löschen? Diese Aktion kann nicht rückgängig gemacht werden.')) {
      return;
    }
    try {
      await axios.delete(`${API}/authority/employees/${employeeId}`);
      toast.success('Mitarbeiter gelöscht');
      fetchEmployees();
    } catch (error) {
      toast.error('Fehler beim Löschen');
    }
  };

  const handleChangeEmployeePassword = async () => {
    if (!newPassword || newPassword.length < 6) {
      toast.error('Passwort muss mindestens 6 Zeichen haben');
      return;
    }
    try {
      await axios.patch(`${API}/authority/employees/${selectedEmployee.id}/password`, {
        new_password: newPassword
      });
      toast.success('Passwort geändert');
      setPasswordDialogOpen(false);
      setNewPassword('');
      setSelectedEmployee(null);
    } catch (error) {
      toast.error('Fehler beim Ändern des Passworts');
    }
  };

  const handleGetLocation = () => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        async (pos) => {
          const { latitude, longitude } = pos.coords;
          setPosition([latitude, longitude]);

          // Reverse geocoding with proper User-Agent for Nominatim policy compliance
          try {
            const response = await fetch(
              `https://nominatim.openstreetmap.org/reverse?format=json&lat=${latitude}&lon=${longitude}`,
              {
                headers: {
                  'User-Agent': 'ImpoundPro/1.0 (Fahrzeug-Verwahrung-App)'
                }
              }
            );
            const data = await response.json();
            setLocationAddress(data.display_name || `${latitude}, ${longitude}`);
          } catch {
            setLocationAddress(`${latitude.toFixed(6)}, ${longitude.toFixed(6)}`);
          }
        },
        (error) => {
          toast.error('Standort konnte nicht ermittelt werden');
        }
      );
    }
  };

  const handlePhotoUpload = async (e) => {
    const files = Array.from(e.target.files);
    if (photos.length + files.length > 5) {
      toast.error('Maximal 5 Fotos erlaubt');
      return;
    }

    toast.info('Fotos werden komprimiert...');

    for (const file of files) {
      try {
        const compressedImage = await compressImage(file, 1200, 0.7);
        setPhotos(prev => [...prev, compressedImage]);
      } catch (error) {
        console.error('Compression error:', error);
      }
    }
    toast.success('Fotos komprimiert');
  };

  const removePhoto = (index) => {
    setPhotos(prev => prev.filter((_, i) => i !== index));
  };

  const handleSubmitJob = async (e) => {
    e.preventDefault();

    // Validierung: Kennzeichen ODER FIN und Grund sind Pflicht, Position ODER Adresse
    if ((!licensePlate && !vin) || !towReason) {
      toast.error('Bitte füllen Sie mindestens Kennzeichen oder FIN sowie den Abschleppgrund aus');
      return;
    }

    if (!position && !locationAddress) {
      toast.error('Bitte geben Sie einen Standort ein oder erfassen Sie GPS-Koordinaten');
      return;
    }

    // Validate Sicherstellung fields
    if (jobType === 'sicherstellung' && !sicherstellungReason) {
      toast.error('Bitte wählen Sie einen Grund für die Sicherstellung');
      return;
    }

    // Wenn keine Position, verwende Standardkoordinaten (Berlin Mitte)
    const lat = position ? position[0] : 52.52;
    const lng = position ? position[1] : 13.405;

    setSubmitting(true);
    try {
      const jobData = {
        license_plate: licensePlate.toUpperCase(),
        vin: vin || null,
        tow_reason: towReason,
        location_address: locationAddress || `${lat.toFixed(6)}, ${lng.toFixed(6)}`,
        location_lat: lat,
        location_lng: lng,
        photos: photos,
        notes: notes || null,
        assigned_service_id: selectedServiceId || null,
        // NEW: Job type and Sicherstellung fields
        job_type: jobType,
        sicherstellung_reason: jobType === 'sicherstellung' ? sicherstellungReason : null,
        vehicle_category: vehicleCategory || null,
        // NEW: Target yard model
        target_yard: targetYard,
        // Authority yard location (when target_yard = "authority_yard")
        authority_yard_id: targetYard === 'authority_yard' ? selectedYardId : null,
        authority_yard_name: targetYard === 'authority_yard' ? selectedYard?.name : null,
        authority_yard_address: targetYard === 'authority_yard' ? selectedYard?.address : null,
        authority_yard_lat: targetYard === 'authority_yard' ? selectedYard?.lat : null,
        authority_yard_lng: targetYard === 'authority_yard' ? selectedYard?.lng : null,
        authority_yard_phone: targetYard === 'authority_yard' ? selectedYard?.phone : null,
        // Authority pricing (when target_yard = "authority_yard")
        authority_price_category_id: targetYard === 'authority_yard' ? selectedPriceCategoryId : null,
        authority_price_category_name: targetYard === 'authority_yard' ? selectedPriceCategory?.name : null,
        authority_base_price: targetYard === 'authority_yard' ? selectedPriceCategory?.base_price : null,
        authority_daily_rate: targetYard === 'authority_yard' ? selectedPriceCategory?.daily_rate : null,
        // Weight category from towing service (when target_yard = "service_yard")
        weight_category_id: targetYard === 'service_yard' ? selectedWeightCategoryId : null,
        weight_category_name: targetYard === 'service_yard' ? selectedWeightCategory?.name : null,
        weight_category_surcharge: targetYard === 'service_yard' ? selectedWeightCategory?.surcharge : null,
        ordering_authority: jobType === 'sicherstellung' ? orderingAuthority : null,
        contact_attempts: jobType === 'sicherstellung' ? contactAttempts : null,
        contact_attempts_notes: jobType === 'sicherstellung' && contactAttempts ? contactAttemptsNotes : null,
        estimated_vehicle_value: jobType === 'sicherstellung' && estimatedVehicleValue ? parseFloat(estimatedVehicleValue) : null
      };

      const idempotencyKey = crypto.randomUUID();
      await axios.post(`${API}/jobs`, jobData, {
        headers: {
          'Idempotency-Key': idempotencyKey
        }
      });
      toast.success('Auftrag erfolgreich erstellt');

      // Reset form
      setLicensePlate('');
      setVin('');
      setTowReason('');
      setLocationAddress('');
      setPosition(null);
      setPhotos([]);
      setNotes('');
      setSelectedServiceId('');
      setJobType('towing');
      setSicherstellungReason('');
      setVehicleCategory('');
      setTargetYard(authoritySettings.yard_model || 'service_yard');
      setSelectedYardId('');
      setSelectedYard(null);
      setSelectedPriceCategoryId('');
      setSelectedPriceCategory(null);
      setSelectedWeightCategoryId('');
      setSelectedWeightCategory(null);
      setServiceWeightCategories([]);
      setOrderingAuthority('');
      setContactAttempts(false);
      setContactAttemptsNotes('');
      setEstimatedVehicleValue('');

      fetchJobs();
      setActiveTab('jobs');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Fehler beim Erstellen des Auftrags');
    } finally {
      setSubmitting(false);
    }
  };

  const handleLinkService = async () => {
    if (!serviceCodeInput.trim()) return;

    try {
      const response = await axios.post(`${API}/services/link`, { service_code: serviceCodeInput });
      toast.success(`${response.data.service_name} erfolgreich verknüpft`);
      setServiceCodeInput('');
      setLinkDialogOpen(false);
      fetchLinkedServices();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Fehler beim Verknüpfen');
    }
  };

  const handleUnlinkService = async (serviceId) => {
    try {
      await axios.delete(`${API}/services/unlink/${serviceId}`);
      toast.success('Abschleppdienst entfernt');
      fetchLinkedServices();
    } catch (error) {
      toast.error('Fehler beim Entfernen');
    }
  };

  // NEW: Open edit dialog for job
  const openEditJobDialog = (job) => {
    setSelectedJobForEdit(job);
    setEditJobData({
      license_plate: job.license_plate || '',
      vin: job.vin || '',
      tow_reason: job.tow_reason || '',
      notes: job.notes || '',
      location_address: job.location_address || '',
      location_lat: job.location_lat || null,
      location_lng: job.location_lng || null
    });
    if (job.location_lat && job.location_lng) {
      setEditJobPosition([job.location_lat, job.location_lng]);
    } else {
      setEditJobPosition(null);
    }
    setEditJobDialogOpen(true);
  };

  // NEW: Save edited job data
  const handleSaveJobData = async () => {
    if (!selectedJobForEdit) return;

    setEditingJobData(true);
    try {
      const dataToSend = {
        ...editJobData,
        location_lat: editJobPosition ? editJobPosition[0] : editJobData.location_lat,
        location_lng: editJobPosition ? editJobPosition[1] : editJobData.location_lng
      };

      const response = await axios.patch(`${API}/jobs/${selectedJobForEdit.id}/edit-data`, dataToSend);

      // Update local state
      setJobs(jobs.map(j => j.id === selectedJobForEdit.id ? response.data : j));

      toast.success('Daten erfolgreich aktualisiert');
      setEditJobDialogOpen(false);
    } catch (error) {
      console.error('Error updating job data:', error);
      toast.error(error.response?.data?.detail || 'Fehler beim Speichern der Daten');
    } finally {
      setEditingJobData(false);
    }
  };

  // NEW: Delete job
  const handleDeleteJob = async (job) => {
    if (!window.confirm(`Auftrag ${job.job_number} wirklich löschen? Diese Aktion kann nicht rückgängig gemacht werden.`)) {
      return;
    }

    setDeletingJob(job.id);
    try {
      await axios.delete(`${API}/jobs/${job.id}`);

      // Remove from local state
      setJobs(jobs.filter(j => j.id !== job.id));

      toast.success(`Auftrag ${job.job_number} wurde gelöscht`);
    } catch (error) {
      console.error('Error deleting job:', error);
      toast.error(error.response?.data?.detail || 'Fehler beim Löschen des Auftrags');
    } finally {
      setDeletingJob(null);
    }
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

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center gap-3">
              <Car className="h-8 w-8 text-slate-900" />
              <div className="hidden sm:block">
                <h1 className="font-bold text-lg text-slate-900" style={{ fontFamily: 'Chivo, sans-serif' }}>
                  Behörden-Dashboard
                </h1>
                <p className="text-xs text-slate-500">{user?.authority_name}</p>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <span className="hidden md:block text-sm text-slate-600">
                {user?.name}
              </span>
              <Button
                data-testid="logout-btn"
                variant="outline"
                size="sm"
                onClick={logout}
                className="flex items-center gap-2"
              >
                <LogOut className="h-4 w-4" />
                <span className="hidden sm:inline">Abmelden</span>
              </Button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 py-6">
        {/* Dienstnummer Badge */}
        {user?.dienstnummer && (
          <Card className="mb-6 border-blue-200 bg-blue-50">
            <CardContent className="py-3">
              <div className="flex items-center gap-3">
                <Badge className="h-5 w-5 text-blue-600" />
                <div>
                  <span className="text-sm text-blue-700">Ihre Dienstnummer: </span>
                  <span className="font-mono font-bold text-blue-900">{user.dienstnummer}</span>
                </div>
                {!user?.is_main_authority && (
                  <span className="text-xs text-blue-600 ml-2">(Mitarbeiter-Account)</span>
                )}
              </div>
            </CardContent>
          </Card>
        )}

        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="mb-6">
            <TabsTrigger data-testid="tab-new-job" value="new" className="flex items-center gap-2">
              <Plus className="h-4 w-4" />
              Neuer Auftrag
            </TabsTrigger>
            <TabsTrigger data-testid="tab-my-jobs" value="jobs" className="flex items-center gap-2">
              <FileText className="h-4 w-4" />
              {user?.is_main_authority ? 'Alle Aufträge' : 'Meine Aufträge'}
            </TabsTrigger>
            {authoritySettings.yard_model === 'authority_yard' && (
              <TabsTrigger data-testid="tab-yard" value="yard" className="flex items-center gap-2">
                <Building2 className="h-4 w-4" />
                Im Hof ({jobs.filter(j => j.status === 'delivered_to_authority' && j.target_yard === 'authority_yard').length})
              </TabsTrigger>
            )}
            {/* Offene Leerfahrten Tab */}
            {jobs.filter(j => j.is_empty_trip && j.empty_trip_reason === 'driver_not_found' && (j.payment_amount === 0 || !j.payment_amount)).length > 0 && (
              <TabsTrigger data-testid="tab-empty-trips" value="empty-trips" className="flex items-center gap-2 text-red-600">
                <Car className="h-4 w-4" />
                Offene Leerfahrten ({jobs.filter(j => j.is_empty_trip && j.empty_trip_reason === 'driver_not_found' && (j.payment_amount === 0 || !j.payment_amount)).length})
              </TabsTrigger>
            )}
            <TabsTrigger data-testid="tab-services" value="services" className="flex items-center gap-2">
              <LinkIcon className="h-4 w-4" />
              Abschleppdienste
            </TabsTrigger>
            {user?.is_main_authority && (
              <TabsTrigger data-testid="tab-employees" value="employees" className="flex items-center gap-2">
                <Users className="h-4 w-4" />
                Mitarbeiter ({employees.length})
              </TabsTrigger>
            )}
            <TabsTrigger data-testid="tab-profile" value="profile" className="flex items-center gap-2">
              <User className="h-4 w-4" />
              Profil
            </TabsTrigger>
            <TabsTrigger data-testid="tab-settings" value="settings" className="flex items-center gap-2">
              <Settings className="h-4 w-4" />
              Einstellungen
            </TabsTrigger>
          </TabsList>

          {/* New Job Tab */}
          <TabsContent value="new">
            <form onSubmit={handleSubmitJob}>
              <div className="grid lg:grid-cols-2 gap-6">
                {/* Vehicle Info */}
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Car className="h-5 w-5" />
                      Fahrzeugdaten
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    {/* NEW: Job Type Selection */}
                    <div className="space-y-3">
                      <Label>Art des Auftrags *</Label>
                      <div className="flex gap-4">
                        <label className={`flex items-center gap-2 p-3 border rounded-lg cursor-pointer transition-colors ${jobType === 'towing' ? 'border-blue-500 bg-blue-50' : 'border-slate-200 hover:bg-slate-50'}`}>
                          <input
                            type="radio"
                            name="jobType"
                            value="towing"
                            checked={jobType === 'towing'}
                            onChange={(e) => setJobType(e.target.value)}
                            className="w-4 h-4"
                          />
                          <span className="font-medium">Abschleppen</span>
                          <span className="text-xs text-slate-500">(Falschparker)</span>
                        </label>
                        <label className={`flex items-center gap-2 p-3 border rounded-lg cursor-pointer transition-colors ${jobType === 'sicherstellung' ? 'border-blue-500 bg-blue-50' : 'border-slate-200 hover:bg-slate-50'}`}>
                          <input
                            type="radio"
                            name="jobType"
                            value="sicherstellung"
                            checked={jobType === 'sicherstellung'}
                            onChange={(e) => setJobType(e.target.value)}
                            className="w-4 h-4"
                          />
                          <span className="font-medium">Sicherstellung</span>
                          <span className="text-xs text-slate-500">(Polizeilich)</span>
                        </label>
                      </div>
                    </div>

                    {/* NEW: Zielort-Auswahl */}
                    {selectedServiceId && (
                      <div className="space-y-3 p-4 bg-slate-50 border border-slate-200 rounded-lg">
                        <Label className="font-semibold">Zielort des Fahrzeugs</Label>
                        <div className="grid grid-cols-2 gap-3">
                          <div
                            onClick={() => {
                              setTargetYard('service_yard');
                              setSelectedPriceCategoryId('');
                              setSelectedPriceCategory(null);
                            }}
                            className={`p-3 border-2 rounded-lg cursor-pointer transition-all ${
                              targetYard === 'service_yard' 
                                ? 'border-blue-500 bg-blue-50' 
                                : 'border-slate-200 hover:border-slate-300'
                            }`}
                          >
                            <div className="flex items-center gap-2">
                              <div className={`w-3 h-3 rounded-full ${
                                targetYard === 'service_yard' ? 'bg-blue-500' : 'bg-slate-300'
                              }`} />
                              <span className="font-medium text-sm">Abschleppdienst-Hof</span>
                            </div>
                          </div>
                          <div
                            onClick={() => {
                              setTargetYard('authority_yard');
                              setSelectedWeightCategoryId('');
                              setSelectedWeightCategory(null);
                            }}
                            className={`p-3 border-2 rounded-lg cursor-pointer transition-all ${
                              targetYard === 'authority_yard' 
                                ? 'border-green-500 bg-green-50' 
                                : 'border-slate-200 hover:border-slate-300'
                            }`}
                          >
                            <div className="flex items-center gap-2">
                              <div className={`w-3 h-3 rounded-full ${
                                targetYard === 'authority_yard' ? 'bg-green-500' : 'bg-slate-300'
                              }`} />
                              <span className="font-medium text-sm">Behörden-Hof</span>
                            </div>
                          </div>
                        </div>
                      </div>
                    )}

                    {/* Hof-Auswahl bei Behörden-Hof */}
                    {selectedServiceId && targetYard === 'authority_yard' && (authoritySettings.yards || []).length > 0 && (
                      <div className="space-y-2 p-4 bg-green-50 border border-green-200 rounded-lg">
                        <Label className="text-green-800">Ziel-Hof auswählen *</Label>
                        <Select 
                          value={selectedYardId} 
                          onValueChange={(value) => {
                            setSelectedYardId(value);
                            const yard = authoritySettings.yards.find(y => y.id === value);
                            setSelectedYard(yard || null);
                          }}
                        >
                          <SelectTrigger>
                            <SelectValue placeholder="Hof auswählen..." />
                          </SelectTrigger>
                          <SelectContent>
                            {authoritySettings.yards.filter(y => y.is_active !== false).map(yard => (
                              <SelectItem key={yard.id} value={yard.id}>
                                <div className="flex flex-col">
                                  <span className="font-medium">{yard.name}</span>
                                  <span className="text-xs text-slate-500">{yard.address}</span>
                                </div>
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                        {selectedYard && (
                          <div className="bg-green-100 border border-green-300 rounded-lg p-3 mt-2 text-sm">
                            <p><strong>Adresse:</strong> {selectedYard.address}</p>
                            {selectedYard.phone && <p><strong>Telefon:</strong> {selectedYard.phone}</p>}
                          </div>
                        )}
                      </div>
                    )}

                    {/* Keine Höfe bei Behörden-Hof */}
                    {selectedServiceId && targetYard === 'authority_yard' && (authoritySettings.yards || []).length === 0 && (
                      <div className="text-sm text-amber-600 bg-amber-50 p-3 rounded-lg border border-amber-200">
                        ⚠️ Keine Höfe angelegt. 
                        <button 
                          type="button"
                          onClick={() => setActiveTab('settings')}
                          className="ml-1 underline font-medium"
                        >
                          Jetzt in Einstellungen anlegen
                        </button>
                      </div>
                    )}

                    {/* Preiskategorie bei Behörden-Hof */}
                    {selectedServiceId && targetYard === 'authority_yard' && (authoritySettings.price_categories || []).length > 0 && (
                      <div className="space-y-2 p-4 bg-green-50 border border-green-200 rounded-lg">
                        <Label className="text-green-800">Fahrzeugkategorie & Verwahrgebühren</Label>
                        <Select 
                          value={selectedPriceCategoryId} 
                          onValueChange={(value) => {
                            setSelectedPriceCategoryId(value);
                            const cat = authoritySettings.price_categories.find(c => c.id === value);
                            setSelectedPriceCategory(cat || null);
                          }}
                        >
                          <SelectTrigger>
                            <SelectValue placeholder="Kategorie wählen..." />
                          </SelectTrigger>
                          <SelectContent>
                            {authoritySettings.price_categories.map(cat => (
                              <SelectItem key={cat.id} value={cat.id}>
                                <div className="flex items-center justify-between w-full gap-4">
                                  <span>{cat.name}</span>
                                  <span className="text-green-600 font-medium">{cat.base_price?.toFixed(2)} €</span>
                                </div>
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                        {selectedPriceCategory && (
                          <div className="bg-green-100 border border-green-300 rounded-lg p-3 mt-2">
                            <div className="flex justify-between text-sm">
                              <span className="text-green-700">Grundpreis (erste 24h):</span>
                              <span className="font-bold text-green-800">{selectedPriceCategory.base_price?.toFixed(2)} €</span>
                            </div>
                            <div className="flex justify-between text-sm mt-1">
                              <span className="text-green-700">Je weitere 24h:</span>
                              <span className="font-medium text-green-800">+ {selectedPriceCategory.daily_rate?.toFixed(2)} €</span>
                            </div>
                          </div>
                        )}
                      </div>
                    )}

                    {/* Keine Preiskategorien bei Behörden-Hof */}
                    {selectedServiceId && targetYard === 'authority_yard' && (authoritySettings.yards || []).length > 0 && (authoritySettings.price_categories || []).length === 0 && (
                      <div className="text-sm text-amber-600 bg-amber-50 p-3 rounded-lg border border-amber-200">
                        ⚠️ Keine Preiskategorien angelegt. 
                        <button 
                          type="button"
                          onClick={() => setActiveTab('settings')}
                          className="ml-1 underline font-medium"
                        >
                          Jetzt in Einstellungen anlegen
                        </button>
                      </div>
                    )}

                    {/* Gewichtskategorie bei Abschleppdienst-Hof */}
                    {selectedServiceId && targetYard === 'service_yard' && serviceWeightCategories.length > 0 && (
                      <div className="space-y-2 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                        <Label className="text-blue-800">Fahrzeuggewicht (Zuschlag vom Abschleppdienst)</Label>
                        <Select 
                          value={selectedWeightCategoryId} 
                          onValueChange={(value) => {
                            setSelectedWeightCategoryId(value);
                            const cat = serviceWeightCategories.find(c => c.id === value);
                            setSelectedWeightCategory(cat || null);
                          }}
                        >
                          <SelectTrigger>
                            <SelectValue placeholder="Gewichtskategorie wählen..." />
                          </SelectTrigger>
                          <SelectContent>
                            {serviceWeightCategories.map(cat => (
                              <SelectItem key={cat.id} value={cat.id}>
                                <div className="flex items-center justify-between w-full gap-4">
                                  <span>{cat.name}</span>
                                  <span className={cat.surcharge > 0 ? "text-orange-600 font-medium" : "text-green-600 font-medium"}>
                                    {cat.surcharge > 0 ? `+${cat.surcharge.toFixed(2)} €` : 'Kein Zuschlag'}
                                  </span>
                                </div>
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                        {selectedWeightCategory && (
                          <div className={`${selectedWeightCategory.surcharge > 0 ? 'bg-orange-50 border-orange-200' : 'bg-green-50 border-green-200'} border rounded-lg p-3 mt-2`}>
                            <div className="flex justify-between text-sm">
                              <span className={selectedWeightCategory.surcharge > 0 ? 'text-orange-700' : 'text-green-700'}>
                                {selectedWeightCategory.name}
                              </span>
                              <span className={`font-bold ${selectedWeightCategory.surcharge > 0 ? 'text-orange-800' : 'text-green-800'}`}>
                                {selectedWeightCategory.surcharge > 0 ? `+${selectedWeightCategory.surcharge.toFixed(2)} €` : 'Kein Zuschlag'}
                              </span>
                            </div>
                          </div>
                        )}
                      </div>
                    )}

                    {/* Sicherstellung-specific fields */}
                    {jobType === 'sicherstellung' && (
                      <div className="space-y-4 p-4 bg-amber-50 border border-amber-200 rounded-lg">
                        <h4 className="font-semibold text-amber-800">Sicherstellungs-Details</h4>

                        <div className="grid md:grid-cols-2 gap-4">
                          <div className="space-y-2">
                            <Label>Grund der Sicherstellung *</Label>
                            <Select value={sicherstellungReason} onValueChange={setSicherstellungReason}>
                              <SelectTrigger>
                                <SelectValue placeholder="Grund auswählen" />
                              </SelectTrigger>
                              <SelectContent>
                                <SelectItem value="betriebsmittel">Auslaufende Betriebsmittel</SelectItem>
                                <SelectItem value="gestohlen">Gestohlenes Fahrzeug / Fahndung</SelectItem>
                                <SelectItem value="eigentumssicherung">Eigentumssicherung (wertvoll/ungesichert)</SelectItem>
                                <SelectItem value="technische_maengel">Technische Mängel / Beweissicherung</SelectItem>
                                <SelectItem value="strafrechtlich">Strafrechtliche Beschlagnahme</SelectItem>
                              </SelectContent>
                            </Select>
                          </div>

                          <div className="space-y-2">
                            <Label>Anordnende Stelle</Label>
                            <Select value={orderingAuthority} onValueChange={setOrderingAuthority}>
                              <SelectTrigger>
                                <SelectValue placeholder="Stelle auswählen" />
                              </SelectTrigger>
                              <SelectContent>
                                <SelectItem value="schutzpolizei">Schutzpolizei</SelectItem>
                                <SelectItem value="kriminalpolizei">Kriminalpolizei</SelectItem>
                                <SelectItem value="staatsanwaltschaft">Staatsanwaltschaft</SelectItem>
                                <SelectItem value="sachverstaendiger">Technischer Sachverständiger</SelectItem>
                              </SelectContent>
                            </Select>
                          </div>

                          <div className="space-y-2">
                            <Label>Geschätzter Fahrzeugwert (€)</Label>
                            <Input
                              type="number"
                              value={estimatedVehicleValue}
                              onChange={(e) => setEstimatedVehicleValue(e.target.value)}
                              placeholder="z.B. 15000"
                            />
                          </div>
                        </div>

                        <div className="space-y-2">
                          <div className="flex items-center gap-2">
                            <input
                              type="checkbox"
                              id="contactAttempts"
                              checked={contactAttempts}
                              onChange={(e) => setContactAttempts(e.target.checked)}
                              className="w-4 h-4"
                            />
                            <Label htmlFor="contactAttempts" className="cursor-pointer">
                              Telefonische Kontaktversuche durchgeführt
                            </Label>
                          </div>
                          {contactAttempts && (
                            <Textarea
                              value={contactAttemptsNotes}
                              onChange={(e) => setContactAttemptsNotes(e.target.value)}
                              placeholder="Dokumentation der Kontaktversuche..."
                              rows={2}
                              className="mt-2"
                            />
                          )}
                        </div>
                      </div>
                    )}

                    <div className="space-y-2">
                      <Label htmlFor="licensePlate">Kennzeichen (oder FIN) *</Label>
                      <Input
                        data-testid="job-license-plate-input"
                        id="licensePlate"
                        value={licensePlate}
                        onChange={(e) => setLicensePlate(e.target.value.toUpperCase())}
                        placeholder="B-AB 1234"
                        className="license-plate-input text-xl"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="vin">Fahrzeug-Identifizierungsnummer (FIN)</Label>
                      <Input
                        data-testid="job-vin-input"
                        id="vin"
                        value={vin}
                        onChange={(e) => setVin(e.target.value.toUpperCase())}
                        placeholder="WVWZZZ3CZWE123456"
                        className="font-mono"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="towReason">Abschleppgrund *</Label>
                      <Select value={towReason} onValueChange={setTowReason}>
                        <SelectTrigger>
                          <SelectValue placeholder="Grund auswählen" />
                        </SelectTrigger>
                        <SelectContent className="max-h-[300px]">
                          <SelectItem value="Parken im Parkverbot">Parken im Parkverbot</SelectItem>
                          <SelectItem value="Parken in Feuerwehrzufahrt">Parken in Feuerwehrzufahrt</SelectItem>
                          <SelectItem value="Parken auf Behindertenparkplatz">Parken auf Behindertenparkplatz</SelectItem>
                          <SelectItem value="Zugeparkte Ausfahrt">Zugeparkte Ausfahrt</SelectItem>
                          <SelectItem value="Gefährdendes Parken">Gefährdendes Parken</SelectItem>
                          <SelectItem value="Fahrzeug ohne gültige Zulassung">Fahrzeug ohne gültige Zulassung im öffentlichen Raum</SelectItem>
                          <SelectItem value="Fahrzeug ohne Kennzeichen">Fahrzeug ohne Kennzeichen</SelectItem>
                          <SelectItem value="Blockieren einer Feuerwehrzufahrt">Blockieren einer Feuerwehrzufahrt</SelectItem>
                          <SelectItem value="Blockieren von Rettungswegen">Blockieren von Rettungswegen</SelectItem>
                          <SelectItem value="Blockieren von Notausfahrten">Blockieren von Notausfahrten</SelectItem>
                          <SelectItem value="Parken im Sicherheitsbereich">Parken im Sicherheitsbereich von Polizei- oder Feuerwehreinsätzen</SelectItem>
                          <SelectItem value="Parken auf E-Auto-Ladeplatz">Parken auf einem E-Auto-Ladeplatz ohne Ladevorgang</SelectItem>
                          <SelectItem value="Parken auf Carsharing-Parkplatz">Parken auf einem Carsharing-Parkplatz ohne Berechtigung</SelectItem>
                          <SelectItem value="Parken auf Bewohnerparkplatz">Parken auf einem Bewohnerparkplatz ohne gültigen Ausweis</SelectItem>
                          <SelectItem value="Öl Verlust">Öl Verlust</SelectItem>
                          <SelectItem value="Sonstiges">Sonstiges</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="notes">Bemerkungen</Label>
                      <Textarea
                        data-testid="job-notes-input"
                        id="notes"
                        value={notes}
                        onChange={(e) => setNotes(e.target.value)}
                        placeholder="Zusätzliche Informationen..."
                        rows={3}
                      />
                    </div>
                  </CardContent>
                </Card>

                {/* Location */}
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <MapPin className="h-5 w-5" />
                      Standort
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <Button
                      data-testid="get-location-btn"
                      type="button"
                      onClick={handleGetLocation}
                      variant="outline"
                      className="w-full"
                    >
                      <MapPin className="h-4 w-4 mr-2" />
                      Aktuellen Standort erfassen
                    </Button>
                    <div className="space-y-2">
                      <Label htmlFor="locationAddress">Adresse *</Label>
                      <Input
                        data-testid="job-location-address-input"
                        id="locationAddress"
                        value={locationAddress}
                        onChange={(e) => setLocationAddress(e.target.value)}
                        placeholder="Straße, Hausnummer, PLZ, Stadt"
                        required
                      />
                    </div>
                    <div className="map-container h-48">
                      <MapContainer
                        center={position || [52.520008, 13.404954]}
                        zoom={position ? 16 : 10}
                        scrollWheelZoom={true}
                      >
                        <TileLayer
                          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                        />
                        <LocationPicker position={position} setPosition={(pos) => {
                          setPosition(pos);
                          setLocationAddress(`${pos[0].toFixed(6)}, ${pos[1].toFixed(6)}`);
                        }} />
                      </MapContainer>
                    </div>
                    <p className="text-xs text-slate-500">
                      Klicken Sie auf die Karte, um den Standort manuell zu setzen
                    </p>
                  </CardContent>
                </Card>

                {/* Photos */}
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Camera className="h-5 w-5" />
                      Fotos ({photos.length}/5)
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="photo-upload-grid">
                      {[...Array(5)].map((_, index) => (
                        <div
                          key={index}
                          className="photo-upload-slot"
                          onClick={() => index >= photos.length && fileInputRef.current?.click()}
                        >
                          {photos[index] ? (
                            <div className="relative w-full h-full group">
                              <img src={photos[index]} alt={`Foto ${index + 1}`} />
                              <button
                                type="button"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  removePhoto(index);
                                }}
                                className="absolute top-1 right-1 bg-red-500 text-white p-1 rounded opacity-0 group-hover:opacity-100 transition-opacity"
                              >
                                <X className="h-3 w-3" />
                              </button>
                            </div>
                          ) : (
                            <Camera className="h-6 w-6 text-slate-400" />
                          )}
                        </div>
                      ))}
                    </div>
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept="image/*"
                      capture="environment"
                      multiple
                      onChange={handlePhotoUpload}
                      className="hidden"
                    />
                  </CardContent>
                </Card>

                {/* Assign Service */}
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <LinkIcon className="h-5 w-5" />
                      Abschleppdienst zuweisen
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    {linkedServices.length > 0 ? (
                      <Select 
                        value={selectedServiceId} 
                        onValueChange={(value) => {
                          setSelectedServiceId(value);
                          fetchServiceWeightCategories(value);
                          setSelectedWeightCategoryId('');
                          setSelectedWeightCategory(null);
                        }}
                      >
                        <SelectTrigger data-testid="job-service-select">
                          <SelectValue placeholder="Abschleppdienst auswählen" />
                        </SelectTrigger>
                        <SelectContent>
                          {linkedServices.map(service => (
                            <SelectItem key={service.id} value={service.id}>
                              {service.company_name}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    ) : (
                      <div className="text-center py-4">
                        <p className="text-slate-500 mb-3">Keine Abschleppdienste verknüpft</p>
                        <Button
                          type="button"
                          variant="outline"
                          onClick={() => setActiveTab('services')}
                        >
                          Abschleppdienst hinzufügen
                        </Button>
                      </div>
                    )}
                  </CardContent>
                </Card>
              </div>

              <div className="mt-6">
                <Button
                  data-testid="submit-job-btn"
                  type="submit"
                  disabled={submitting}
                  className="w-full md:w-auto h-12 px-8 bg-slate-900 hover:bg-slate-800 text-white"
                >
                  {submitting ? (
                    <div className="loading-spinner mr-2"></div>
                  ) : (
                    <CheckCircle className="h-5 w-5 mr-2" />
                  )}
                  Auftrag erstellen
                </Button>
              </div>
            </form>
          </TabsContent>

          {/* Jobs Tab */}
          <TabsContent value="jobs">
            {/* Filter Section */}
            <Card className="mb-6">
              <CardContent className="py-4">
                <div className="flex flex-wrap items-center gap-4">
                  <Button
                    variant={filterOpen ? "default" : "outline"}
                    size="sm"
                    onClick={() => setFilterOpen(!filterOpen)}
                    className="flex items-center gap-2"
                  >
                    <Filter className="h-4 w-4" />
                    Filter
                    {hasActiveFilters && (
                      <span className="bg-orange-500 text-white text-xs px-1.5 py-0.5 rounded-full">!</span>
                    )}
                  </Button>

                  {hasActiveFilters && (
                    <Button variant="ghost" size="sm" onClick={clearFilters}>
                      Filter zurücksetzen
                    </Button>
                  )}

                  <span className="text-sm text-slate-500 ml-auto">
                    {totalJobs} Auftrag{totalJobs !== 1 ? 'e' : ''} gefunden
                  </span>
                </div>

                {filterOpen && (
                  <div className="mt-4 pt-4 border-t grid sm:grid-cols-4 gap-4">
                    <div className="space-y-2">
                      <Label className="text-sm text-slate-500">Status</Label>
                      <Select value={filterStatus} onValueChange={(val) => { setFilterStatus(val); setCurrentPage(1); }}>
                        <SelectTrigger>
                          <SelectValue placeholder="Alle Status" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="all">Alle Status</SelectItem>
                          <SelectItem value="pending">Ausstehend</SelectItem>
                          <SelectItem value="assigned">Zugewiesen</SelectItem>
                          <SelectItem value="on_site">Vor Ort</SelectItem>
                          <SelectItem value="towed">Abgeschleppt</SelectItem>
                          <SelectItem value="in_yard">Im Hof</SelectItem>
                          <SelectItem value="delivered_to_authority">An Behörde übergeben</SelectItem>
                          <SelectItem value="released">Abgeholt</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-2">
                      <Label className="text-sm text-slate-500">Abschleppdienst</Label>
                      <Select value={filterService} onValueChange={(val) => { setFilterService(val); setCurrentPage(1); }}>
                        <SelectTrigger>
                          <SelectValue placeholder="Alle Dienste" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="all">Alle Abschleppdienste</SelectItem>
                          {linkedServices.map(service => (
                            <SelectItem key={service.id} value={service.id}>
                              {service.company_name}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-2">
                      <Label className="text-sm text-slate-500">Datum von</Label>
                      <Input
                        type="date"
                        value={filterDateFrom}
                        onChange={(e) => { setFilterDateFrom(e.target.value); setCurrentPage(1); }}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label className="text-sm text-slate-500">Datum bis</Label>
                      <Input
                        type="date"
                        value={filterDateTo}
                        onChange={(e) => { setFilterDateTo(e.target.value); setCurrentPage(1); }}
                      />
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Meine Aufträge</CardTitle>
              </CardHeader>
              <CardContent>
                {loading ? (
                  <div className="flex justify-center py-8">
                    <div className="loading-spinner"></div>
                  </div>
                ) : jobs.length === 0 ? (
                  <div className="empty-state">
                    <FileText className="empty-state-icon" />
                    <p>Noch keine Aufträge erstellt</p>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {jobs.map(job => (
                      <div key={job.id} className="job-card">
                        <div className="job-card-header">
                          <div>
                            <p className="job-license-plate">{job.license_plate}</p>
                            <p className="text-sm text-slate-500">{job.job_number}</p>
                          </div>
                          <div className="flex items-center gap-2">
                            {job.created_by_dienstnummer && (
                              <span className="px-2 py-1 bg-blue-100 text-blue-700 text-xs rounded font-mono">
                                {job.created_by_dienstnummer}
                              </span>
                            )}
                            {getStatusBadge(job.status)}
                          </div>
                        </div>
                        <div className="grid sm:grid-cols-2 gap-3 text-sm">
                          <div className="flex items-center gap-2 text-slate-600">
                            <MapPin className="h-4 w-4" />
                            <span className="truncate">{job.location_address}</span>
                          </div>
                          <div className="flex items-center gap-2 text-slate-600">
                            <Clock className="h-4 w-4" />
                            <span>{new Date(job.created_at).toLocaleString('de-DE')}</span>
                          </div>
                        </div>
                        <p className="mt-2 text-sm text-slate-600">
                          Erfasst von: <span className="font-medium">{job.created_by_name}</span>
                          {job.created_by_dienstnummer && (
                            <span className="text-slate-400 ml-1">({job.created_by_dienstnummer})</span>
                          )}
                        </p>
                        {job.assigned_service_name && (
                          <p className="text-sm text-slate-600">
                            Zugewiesen an: <span className="font-medium">{job.assigned_service_name}</span>
                          </p>
                        )}

                        {/* Timeline / Zeiterfassung */}
                        <div className="mt-4 pt-4 border-t">
                          <p className="text-xs font-semibold text-slate-500 mb-2">ZEITERFASSUNG</p>
                          <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 text-xs">
                            <div className={`p-2 rounded ${job.created_at ? 'bg-green-50 border border-green-200' : 'bg-slate-50'}`}>
                              <p className="font-medium text-slate-700">Meldung</p>
                              <p className="text-slate-500">{job.created_at ? new Date(job.created_at).toLocaleString('de-DE') : '-'}</p>
                            </div>
                            <div className={`p-2 rounded ${job.on_site_at ? 'bg-green-50 border border-green-200' : 'bg-slate-50'}`}>
                              <p className="font-medium text-slate-700">Vor Ort</p>
                              <p className="text-slate-500">{job.on_site_at ? new Date(job.on_site_at).toLocaleString('de-DE') : '-'}</p>
                            </div>
                            {job.is_empty_trip ? (
                              <div className={`col-span-1 sm:col-span-3 p-2 rounded ${job.status === 'empty_trip' || job.status === 'released' ? 'bg-orange-50 border border-orange-200' : 'bg-slate-50'}`}>
                                <p className="font-medium text-slate-700">Leerfahrt verzeichnet</p>
                                <p className="text-slate-500">{job.updated_at ? new Date(job.updated_at).toLocaleString('de-DE') : '-'}</p>
                              </div>
                            ) : (
                              <>
                                <div className={`p-2 rounded ${job.towed_at ? 'bg-green-50 border border-green-200' : 'bg-slate-50'}`}>
                                  <p className="font-medium text-slate-700">Abgeschleppt</p>
                                  <p className="text-slate-500">{job.towed_at ? new Date(job.towed_at).toLocaleString('de-DE') : '-'}</p>
                                </div>
                                <div className={`p-2 rounded ${(job.target_yard === 'authority_yard' ? job.delivered_to_authority_at : job.in_yard_at) ? 'bg-green-50 border border-green-200' : 'bg-slate-50'}`}>
                                  <p className="font-medium text-slate-700">{job.target_yard === 'authority_yard' ? 'Im Behörden-Hof' : 'Im Hof'}</p>
                                  <p className="text-slate-500">{(job.target_yard === 'authority_yard' ? job.delivered_to_authority_at : job.in_yard_at) ? new Date(job.target_yard === 'authority_yard' ? job.delivered_to_authority_at : job.in_yard_at).toLocaleString('de-DE') : '-'}</p>
                                </div>
                                <div className={`p-2 rounded ${job.released_at ? 'bg-green-50 border border-green-200' : 'bg-slate-50'}`}>
                                  <p className="font-medium text-slate-700">Abgeholt</p>
                                  <p className="text-slate-500">{job.released_at ? new Date(job.released_at).toLocaleString('de-DE') : '-'}</p>
                                </div>
                              </>
                            )}
                          </div>
                        </div>

                        {/* PDF Download Button - shows when job is released */}
                        {job.status === 'released' && (
                          <div className="mt-4 pt-4 border-t flex justify-end">
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={async () => {
                                try {
                                  const res = await axios.get(`${API}/jobs/${job.id}/pdf/token`);
                                  window.open(`${API}/jobs/${job.id}/pdf?token=${res.data.token}`, '_blank');
                                } catch (error) {
                                  console.error('Error fetching PDF token:', error);
                                  toast.error('PDF konnte nicht generiert werden');
                                }
                              }}
                              className="flex items-center gap-2"
                            >
                              <Download className="h-4 w-4" />
                              PDF herunterladen
                            </Button>
                          </div>
                        )}

                        {/* Edit/Delete Buttons - only show if job is not released */}
                        {job.status !== 'released' && (
                          <div className="mt-4 pt-4 border-t flex justify-between items-center">
                            {/* Delete button - only for early stages */}
                            {['pending', 'assigned', 'on_site'].includes(job.status) ? (
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => handleDeleteJob(job)}
                                disabled={deletingJob === job.id}
                                className="text-red-600 border-red-200 hover:bg-red-50"
                              >
                                {deletingJob === job.id ? (
                                  <>Löscht...</>
                                ) : (
                                  <>
                                    <X className="h-4 w-4 mr-1" />
                                    Löschen
                                  </>
                                )}
                              </Button>
                            ) : (
                              <div />
                            )}

                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => openEditJobDialog(job)}
                              className="text-blue-600 border-blue-200 hover:bg-blue-50"
                            >
                              <Settings className="h-4 w-4 mr-1" />
                              Bearbeiten
                            </Button>
                          </div>
                        )}
                      </div>
                    ))}
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

          {/* Yard Tab - Vehicles at authority yard awaiting release */}
          {authoritySettings.yard_model === 'authority_yard' && (
            <TabsContent value="yard">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Building2 className="h-5 w-5" />
                    Fahrzeuge im Behörden-Hof
                  </CardTitle>
                  <CardDescription>
                    Diese Fahrzeuge wurden vom Abschleppdienst abgeliefert und warten auf Freigabe
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  {jobs.filter(j => j.status === 'delivered_to_authority' && j.target_yard === 'authority_yard').length === 0 ? (
                    <div className="text-center py-8 text-slate-500">
                      <Building2 className="h-12 w-12 mx-auto mb-4 opacity-30" />
                      <p>Keine Fahrzeuge im Hof</p>
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {jobs.filter(j => j.status === 'delivered_to_authority' && j.target_yard === 'authority_yard').map(job => {
                        const costs = calculateAuthorityCosts(job);
                        return (
                          <div key={job.id} className="border rounded-lg p-4 hover:bg-slate-50">
                            <div className="flex items-center justify-between">
                              <div className="flex-1">
                                <div className="flex items-center gap-3">
                                  <span className="font-bold text-lg">{job.license_plate}</span>
                                  <span className="px-2 py-1 rounded-full text-xs font-medium bg-purple-100 text-purple-800">
                                    Im Hof
                                  </span>
                                </div>
                                <p className="text-sm text-slate-500 mt-1">{job.job_number}</p>
                                <div className="mt-2 text-sm">
                                  <p><strong>Grund:</strong> {job.tow_reason}</p>
                                  <p><strong>Kategorie:</strong> {job.authority_price_category_name || 'Nicht zugewiesen'}</p>
                                  <p><strong>Abgeliefert:</strong> {job.delivered_to_authority_at ? new Date(job.delivered_to_authority_at).toLocaleString('de-DE') : '-'}</p>
                                  <p><strong>Tage im Hof:</strong> {costs.days}</p>
                                </div>
                              </div>
                              <div className="text-right">
                                <p className="text-2xl font-bold text-green-600">{costs.total.toFixed(2)} €</p>
                                <p className="text-xs text-slate-500">Geschätzter Betrag</p>
                                <Button
                                  className="mt-3 bg-green-500 hover:bg-green-600"
                                  onClick={() => {
                                    setSelectedYardJob(job);
                                    const c = calculateAuthorityCosts(job);
                                    setReleaseData({
                                      ...releaseData,
                                      payment_amount: c.total.toFixed(2)
                                    });
                                    setReleaseDialogOpen(true);
                                  }}
                                >
                                  <CheckCircle className="h-4 w-4 mr-2" />
                                  Fahrzeug freigeben
                                </Button>
                              </div>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </CardContent>
              </Card>
            </TabsContent>
          )}

          {/* Offene Leerfahrten Tab */}
          <TabsContent value="empty-trips">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-red-700">
                  <Car className="h-5 w-5" />
                  Offene Leerfahrten - Halter kontaktieren
                </CardTitle>
                <CardDescription>
                  Diese Leerfahrten wurden ohne Zahlung erfasst. Bitte kontaktieren Sie die Halter zur Kostenerstattung.
                </CardDescription>
              </CardHeader>
              <CardContent>
                {jobs.filter(j => j.is_empty_trip && j.empty_trip_reason === 'driver_not_found' && (j.payment_amount === 0 || !j.payment_amount)).length === 0 ? (
                  <div className="text-center py-8 text-slate-500">
                    <CheckCircle className="h-12 w-12 mx-auto mb-4 opacity-30 text-green-500" />
                    <p>Keine offenen Leerfahrten</p>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {jobs.filter(j => j.is_empty_trip && j.empty_trip_reason === 'driver_not_found' && (j.payment_amount === 0 || !j.payment_amount)).map(job => (
                      <div key={job.id} className="p-4 bg-red-50 border border-red-200 rounded-lg">
                        <div className="flex items-start justify-between">
                          <div>
                            <div className="flex items-center gap-3 mb-2">
                              <span className="font-bold text-xl">{job.license_plate}</span>
                              <span className="px-2 py-1 rounded-full text-xs font-medium bg-red-100 text-red-800">
                                Kosten offen
                              </span>
                            </div>
                            <p className="text-sm text-slate-600">{job.job_number}</p>
                            <p className="text-sm text-slate-600 mt-1">
                              <strong>Abschleppdienst:</strong> {job.assigned_service_name}
                            </p>
                            <p className="text-sm text-slate-600">
                              <strong>Datum:</strong> {job.created_at ? new Date(job.created_at).toLocaleString('de-DE') : '-'}
                            </p>
                            <p className="text-sm text-slate-600">
                              <strong>Standort:</strong> {job.location_address}
                            </p>
                            {job.service_notes && (
                              <p className="text-sm text-red-700 mt-2 p-2 bg-red-100 rounded">
                                {job.service_notes}
                              </p>
                            )}
                          </div>
                          <div className="text-right">
                            <p className="text-lg font-bold text-red-600">
                              Leerfahrt-Kosten offen
                            </p>
                            <p className="text-xs text-slate-500 mt-1">
                              Halter ermitteln und kontaktieren
                            </p>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* Services Tab */}
          <TabsContent value="services">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between">
                <div>
                  <CardTitle>Verknüpfte Abschleppdienste</CardTitle>
                  {!user?.is_main_authority && (
                    <p className="text-sm text-slate-500 mt-1">
                      Die Verknüpfungen werden vom Haupt-Account verwaltet
                    </p>
                  )}
                </div>
                {/* Only main authority can add services */}
                {user?.is_main_authority && (
                  <Dialog open={linkDialogOpen} onOpenChange={setLinkDialogOpen}>
                    <DialogTrigger asChild>
                      <Button data-testid="add-service-btn" className="bg-slate-900 hover:bg-slate-800">
                        <Plus className="h-4 w-4 mr-2" />
                        Hinzufügen
                      </Button>
                    </DialogTrigger>
                    <DialogContent>
                      <DialogHeader>
                        <DialogTitle>Abschleppdienst verknüpfen</DialogTitle>
                      <DialogDescription>
                        Geben Sie den 6-stelligen Code des Abschleppdienstes ein
                      </DialogDescription>
                    </DialogHeader>
                    <div className="space-y-4 py-4">
                      <Input
                        data-testid="service-code-input"
                        value={serviceCodeInput}
                        onChange={(e) => setServiceCodeInput(e.target.value)}
                        placeholder="z.B. AbCd12"
                        className="text-center font-mono text-lg uppercase"
                        maxLength={6}
                      />
                      <Button
                        data-testid="link-service-btn"
                        onClick={handleLinkService}
                        className="w-full bg-slate-900 hover:bg-slate-800"
                        disabled={serviceCodeInput.length !== 6}
                      >
                        Verknüpfen
                      </Button>
                    </div>
                  </DialogContent>
                </Dialog>
                )}
              </CardHeader>
              <CardContent>
                {linkedServices.length === 0 ? (
                  <div className="empty-state">
                    <LinkIcon className="empty-state-icon" />
                    <p>Noch keine Abschleppdienste verknüpft</p>
                    {user?.is_main_authority ? (
                      <p className="text-sm mt-2">
                        Bitten Sie Ihren Abschleppdienst um den 6-stelligen Verknüpfungscode
                      </p>
                    ) : (
                      <p className="text-sm mt-2">
                        Der Haupt-Account hat noch keine Abschleppdienste verknüpft
                      </p>
                    )}
                  </div>
                ) : (
                  <div className="space-y-3">
                    {linkedServices.map(service => (
                      <div
                        key={service.id}
                        className="flex items-center justify-between p-4 bg-slate-50 rounded-lg"
                      >
                        <div>
                          <p className="font-medium">{service.company_name}</p>
                          <p className="text-sm text-slate-500">{service.phone}</p>
                          {service.address && (
                            <p className="text-sm text-slate-500">{service.address}</p>
                          )}
                        </div>
                        {/* Only main authority can unlink services */}
                        {user?.is_main_authority && (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleUnlinkService(service.id)}
                            className="text-red-600 hover:text-red-700 hover:bg-red-50"
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* Employees Tab - Only for Main Authority */}
          {user?.is_main_authority && (
            <TabsContent value="employees">
              <Card>
                <CardHeader>
                  <div className="flex justify-between items-center">
                    <div>
                      <CardTitle className="flex items-center gap-2">
                        <Users className="h-5 w-5" />
                        Mitarbeiter verwalten
                      </CardTitle>
                      <CardDescription>
                        Mitarbeiter können sich einloggen und Fahrzeuge erfassen
                      </CardDescription>
                    </div>
                    <Button onClick={() => setEmployeeDialogOpen(true)}>
                      <UserPlus className="h-4 w-4 mr-2" />
                      Neuer Mitarbeiter
                    </Button>
                  </div>
                </CardHeader>
                <CardContent>
                  {employees.length === 0 ? (
                    <div className="text-center py-8 text-slate-500">
                      <Users className="h-12 w-12 mx-auto mb-4 opacity-50" />
                      <p>Noch keine Mitarbeiter angelegt</p>
                      <p className="text-sm">Legen Sie Mitarbeiter an, damit diese Fahrzeuge erfassen können</p>
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {employees.map(emp => (
                        <div
                          key={emp.id}
                          className={`flex items-center justify-between p-4 border rounded-lg ${emp.is_blocked ? 'bg-red-50 border-red-200' : 'bg-white'
                            }`}
                        >
                          <div className="flex items-center gap-4">
                            <div className={`w-10 h-10 rounded-full flex items-center justify-center ${emp.is_blocked ? 'bg-red-200' : 'bg-blue-100'
                              }`}>
                              <Users className={`h-5 w-5 ${emp.is_blocked ? 'text-red-600' : 'text-blue-600'}`} />
                            </div>
                            <div>
                              <p className="font-medium">{emp.name}</p>
                              <p className="text-sm text-slate-500">{emp.email}</p>
                            </div>
                            <div className="ml-4 px-3 py-1 bg-slate-100 rounded">
                              <span className="text-xs text-slate-500">Dienstnummer:</span>
                              <span className="ml-1 font-mono font-bold text-slate-700">{emp.dienstnummer}</span>
                            </div>
                            {emp.is_blocked && (
                              <span className="px-2 py-1 bg-red-100 text-red-700 text-xs rounded">Gesperrt</span>
                            )}
                          </div>
                          <div className="flex items-center gap-2">
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => {
                                setSelectedEmployee(emp);
                                setPasswordDialogOpen(true);
                              }}
                              title="Passwort ändern"
                            >
                              <Key className="h-4 w-4" />
                            </Button>
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => handleBlockEmployee(emp.id, !emp.is_blocked)}
                              title={emp.is_blocked ? 'Entsperren' : 'Sperren'}
                            >
                              {emp.is_blocked ? <Unlock className="h-4 w-4" /> : <Lock className="h-4 w-4" />}
                            </Button>
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => handleDeleteEmployee(emp.id)}
                              className="text-red-600 hover:text-red-700"
                              title="Löschen"
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            </TabsContent>
          )}

          {/* Profile Tab */}
          <TabsContent value="profile">
            <TwoFactorSetup />
          </TabsContent>

          {/* Settings Tab */}
          <TabsContent value="settings">
            <div className="space-y-6">
              {/* Hof-Modell */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Settings className="h-5 w-5" />
                    Hof-Modell
                  </CardTitle>
                  <CardDescription>
                    Wählen Sie, wohin abgeschleppte Fahrzeuge gebracht werden
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div
                      onClick={() => setAuthoritySettings({...authoritySettings, yard_model: 'service_yard'})}
                      className={`p-4 border-2 rounded-lg cursor-pointer transition-all ${
                        authoritySettings.yard_model === 'service_yard' 
                          ? 'border-blue-500 bg-blue-50' 
                          : 'border-slate-200 hover:border-slate-300'
                      }`}
                    >
                      <div className="flex items-center gap-2 mb-2">
                        <div className={`w-4 h-4 rounded-full border-2 ${
                          authoritySettings.yard_model === 'service_yard' 
                            ? 'border-blue-500 bg-blue-500' 
                            : 'border-slate-300'
                        }`}>
                          {authoritySettings.yard_model === 'service_yard' && (
                            <CheckCircle className="w-3 h-3 text-white" />
                          )}
                        </div>
                        <span className="font-semibold">Abschleppdienst-Hof</span>
                      </div>
                      <p className="text-sm text-slate-600">
                        Fahrzeuge werden auf den Hof des Abschleppdienstes gebracht.
                        Der Abschleppdienst kassiert vom Halter.
                      </p>
                    </div>

                    <div
                      onClick={() => setAuthoritySettings({...authoritySettings, yard_model: 'authority_yard'})}
                      className={`p-4 border-2 rounded-lg cursor-pointer transition-all ${
                        authoritySettings.yard_model === 'authority_yard' 
                          ? 'border-green-500 bg-green-50' 
                          : 'border-slate-200 hover:border-slate-300'
                      }`}
                    >
                      <div className="flex items-center gap-2 mb-2">
                        <div className={`w-4 h-4 rounded-full border-2 ${
                          authoritySettings.yard_model === 'authority_yard' 
                            ? 'border-green-500 bg-green-500' 
                            : 'border-slate-300'
                        }`}>
                          {authoritySettings.yard_model === 'authority_yard' && (
                            <CheckCircle className="w-3 h-3 text-white" />
                          )}
                        </div>
                        <span className="font-semibold">Behörden-Hof</span>
                      </div>
                      <p className="text-sm text-slate-600">
                        Fahrzeuge werden auf den Hof der Behörde gebracht.
                        Die Behörde kassiert vom Halter, Abschleppdienst bekommt Rechnung.
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Preiskategorien (nur bei Behörden-Hof) */}
              {authoritySettings.yard_model === 'authority_yard' && (
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Euro className="h-5 w-5" />
                      Preiskategorien
                    </CardTitle>
                    <CardDescription>
                      Definieren Sie Ihre Verwahrgebühren nach Fahrzeugtyp
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    {/* Bestehende Kategorien */}
                    {(authoritySettings.price_categories || []).length > 0 && (
                      <div className="space-y-2">
                        {authoritySettings.price_categories.map((cat) => (
                          <div key={cat.id} className="flex items-center justify-between p-3 bg-slate-50 rounded-lg border">
                            <div>
                              <span className="font-medium">{cat.name}</span>
                            </div>
                            <div className="flex items-center gap-4">
                              <div className="text-sm">
                                <span className="text-green-600 font-bold">{cat.base_price?.toFixed(2)} €</span>
                                <span className="text-slate-500 ml-2">+ {cat.daily_rate?.toFixed(2)} €/Tag</span>
                              </div>
                              <button
                                type="button"
                                onClick={() => handleRemovePriceCategory(cat.id)}
                                className="text-red-500 hover:text-red-700"
                              >
                                <X className="h-4 w-4" />
                              </button>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Neue Kategorie hinzufügen */}
                    <div className="p-4 bg-blue-50 rounded-lg border border-blue-200 space-y-3">
                      <p className="text-sm font-medium text-blue-800">Neue Kategorie hinzufügen</p>
                      <div className="grid grid-cols-3 gap-3">
                        <Input
                          placeholder="Name (z.B. PKW bis 4t)"
                          value={newPriceCategory.name}
                          onChange={(e) => setNewPriceCategory({...newPriceCategory, name: e.target.value})}
                        />
                        <Input
                          type="number"
                          step="0.01"
                          placeholder="Grundpreis (€)"
                          value={newPriceCategory.base_price}
                          onChange={(e) => setNewPriceCategory({...newPriceCategory, base_price: e.target.value})}
                        />
                        <Input
                          type="number"
                          step="0.01"
                          placeholder="Pro Tag (€)"
                          value={newPriceCategory.daily_rate}
                          onChange={(e) => setNewPriceCategory({...newPriceCategory, daily_rate: e.target.value})}
                        />
                      </div>
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={handleAddPriceCategory}
                        className="w-full"
                      >
                        <Plus className="h-4 w-4 mr-2" />
                        Kategorie hinzufügen
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Höfe verwalten (nur bei Behörden-Hof) */}
              {authoritySettings.yard_model === 'authority_yard' && (
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Building2 className="h-5 w-5" />
                      Abschlepphöfe
                    </CardTitle>
                    <CardDescription>
                      Verwalten Sie Ihre Abschlepphöfe mit Adresse und Telefonnummer
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    {/* Bestehende Höfe */}
                    {(authoritySettings.yards || []).length > 0 && (
                      <div className="space-y-2">
                        {authoritySettings.yards.map((yard) => (
                          <div key={yard.id} className="flex items-center justify-between p-3 bg-slate-50 rounded-lg border">
                            <div>
                              <span className="font-medium">{yard.name}</span>
                              <p className="text-sm text-slate-500">{yard.address}</p>
                              {yard.phone && <p className="text-sm text-slate-500">📞 {yard.phone}</p>}
                            </div>
                            <button
                              type="button"
                              onClick={() => handleRemoveYard(yard.id)}
                              className="text-red-500 hover:text-red-700"
                            >
                              <X className="h-4 w-4" />
                            </button>
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Neuen Hof hinzufügen */}
                    <div className="p-4 bg-green-50 rounded-lg border border-green-200 space-y-3">
                      <p className="text-sm font-medium text-green-800">Neuen Hof hinzufügen</p>
                      <div className="space-y-3">
                        <Input
                          placeholder="Name (z.B. 'Haupthof', 'Außenstelle Nord')"
                          value={newYard.name}
                          onChange={(e) => setNewYard({...newYard, name: e.target.value})}
                        />
                        <Input
                          placeholder="Adresse (Straße, PLZ Ort)"
                          value={newYard.address}
                          onChange={(e) => setNewYard({...newYard, address: e.target.value})}
                        />
                        <Input
                          placeholder="Telefonnummer (optional)"
                          value={newYard.phone}
                          onChange={(e) => setNewYard({...newYard, phone: e.target.value})}
                        />
                      </div>
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={handleAddYard}
                        className="w-full"
                      >
                        <Plus className="h-4 w-4 mr-2" />
                        Hof hinzufügen
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Speichern-Button */}
              <Button
                onClick={handleSaveAuthoritySettings}
                disabled={savingSettings}
                className="w-full md:w-auto bg-slate-900 hover:bg-slate-800"
              >
                {savingSettings ? 'Speichern...' : 'Einstellungen speichern'}
              </Button>
            </div>
          </TabsContent>

        </Tabs>
      </main>

      {/* Create Employee Dialog */}
      <Dialog open={employeeDialogOpen} onOpenChange={setEmployeeDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Neuen Mitarbeiter anlegen</DialogTitle>
            <DialogDescription>
              Der Mitarbeiter erhält automatisch eine Dienstnummer und kann sich einloggen
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleCreateEmployee} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="empName">Name *</Label>
              <Input
                id="empName"
                value={newEmployeeName}
                onChange={(e) => setNewEmployeeName(e.target.value)}
                placeholder="Max Mustermann"
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="empEmail">E-Mail *</Label>
              <Input
                id="empEmail"
                type="email"
                value={newEmployeeEmail}
                onChange={(e) => setNewEmployeeEmail(e.target.value)}
                placeholder="mitarbeiter@behoerde.de"
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="empPassword">Passwort *</Label>
              <Input
                id="empPassword"
                type="password"
                value={newEmployeePassword}
                onChange={(e) => setNewEmployeePassword(e.target.value)}
                placeholder="Mindestens 6 Zeichen"
                required
              />
            </div>
            <Button type="submit" className="w-full" disabled={creatingEmployee}>
              {creatingEmployee ? 'Wird angelegt...' : 'Mitarbeiter anlegen'}
            </Button>
          </form>
        </DialogContent>
      </Dialog>

      {/* Change Password Dialog */}
      <Dialog open={passwordDialogOpen} onOpenChange={setPasswordDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Passwort ändern</DialogTitle>
            <DialogDescription>
              Neues Passwort für {selectedEmployee?.name} setzen
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="newPwd">Neues Passwort</Label>
              <Input
                id="newPwd"
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                placeholder="Mindestens 6 Zeichen"
              />
            </div>
            <Button onClick={handleChangeEmployeePassword} className="w-full">
              Passwort ändern
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Edit Job Data Dialog */}
      <Dialog open={editJobDialogOpen} onOpenChange={setEditJobDialogOpen}>
        <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Settings className="h-5 w-5" />
              Auftrag bearbeiten
            </DialogTitle>
            <DialogDescription>
              Korrigieren Sie Kennzeichen, FIN, Standort oder andere Angaben
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="edit-license-plate">Kennzeichen</Label>
              <Input
                id="edit-license-plate"
                value={editJobData.license_plate}
                onChange={(e) => setEditJobData(prev => ({ ...prev, license_plate: e.target.value.toUpperCase() }))}
                placeholder="z.B. B-AB 1234"
                className="text-lg font-mono"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit-vin">Fahrzeug-Identnummer (FIN)</Label>
              <Input
                id="edit-vin"
                value={editJobData.vin}
                onChange={(e) => setEditJobData(prev => ({ ...prev, vin: e.target.value.toUpperCase() }))}
                placeholder="17-stellige FIN"
                className="font-mono"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit-tow-reason">Abschleppgrund</Label>
              <Select
                value={editJobData.tow_reason}
                onValueChange={(value) => setEditJobData(prev => ({ ...prev, tow_reason: value }))}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Grund auswählen..." />
                </SelectTrigger>
                <SelectContent className="max-h-[300px]">
                  <SelectItem value="Parken im Parkverbot">Parken im Parkverbot</SelectItem>
                  <SelectItem value="Parken in Feuerwehrzufahrt">Parken in Feuerwehrzufahrt</SelectItem>
                  <SelectItem value="Parken auf Behindertenparkplatz">Parken auf Behindertenparkplatz</SelectItem>
                  <SelectItem value="Zugeparkte Ausfahrt">Zugeparkte Ausfahrt</SelectItem>
                  <SelectItem value="Gefährdendes Parken">Gefährdendes Parken</SelectItem>
                  <SelectItem value="Fahrzeug ohne gültige Zulassung">Fahrzeug ohne gültige Zulassung im öffentlichen Raum</SelectItem>
                  <SelectItem value="Fahrzeug ohne Kennzeichen">Fahrzeug ohne Kennzeichen</SelectItem>
                  <SelectItem value="Blockieren einer Feuerwehrzufahrt">Blockieren einer Feuerwehrzufahrt</SelectItem>
                  <SelectItem value="Blockieren von Rettungswegen">Blockieren von Rettungswegen</SelectItem>
                  <SelectItem value="Blockieren von Notausfahrten">Blockieren von Notausfahrten</SelectItem>
                  <SelectItem value="Parken im Sicherheitsbereich">Parken im Sicherheitsbereich von Polizei- oder Feuerwehreinsätzen</SelectItem>
                  <SelectItem value="Parken auf E-Auto-Ladeplatz">Parken auf einem E-Auto-Ladeplatz ohne Ladevorgang</SelectItem>
                  <SelectItem value="Parken auf Carsharing-Parkplatz">Parken auf einem Carsharing-Parkplatz ohne Berechtigung</SelectItem>
                  <SelectItem value="Parken auf Bewohnerparkplatz">Parken auf einem Bewohnerparkplatz ohne gültigen Ausweis</SelectItem>
                  <SelectItem value="Öl Verlust">Öl Verlust</SelectItem>
                  <SelectItem value="Sonstiges">Sonstiges</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit-notes">Bemerkungen</Label>
              <Textarea
                id="edit-notes"
                value={editJobData.notes}
                onChange={(e) => setEditJobData(prev => ({ ...prev, notes: e.target.value }))}
                placeholder="Zusätzliche Informationen..."
                rows={2}
              />
            </div>

            {/* Location Edit Section */}
            <div className="space-y-2 pt-4 border-t">
              <Label className="flex items-center gap-2">
                <MapPin className="h-4 w-4" />
                Standort ändern
              </Label>
              <Input
                value={editJobData.location_address}
                onChange={(e) => setEditJobData(prev => ({ ...prev, location_address: e.target.value }))}
                placeholder="Adresse eingeben..."
              />
              <div className="h-48 rounded-lg overflow-hidden border">
                <MapContainer
                  center={editJobPosition || [52.52, 13.405]}
                  zoom={editJobPosition ? 15 : 10}
                  className="h-full w-full"
                  key={editJobDialogOpen ? 'auth-edit-map-open' : 'auth-edit-map-closed'}
                >
                  <TileLayer
                    attribution='&copy; OpenStreetMap'
                    url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                  />
                  <LocationPicker
                    position={editJobPosition}
                    setPosition={async (pos) => {
                      setEditJobPosition(pos);
                      setEditJobData(prev => ({
                        ...prev,
                        location_lat: pos[0],
                        location_lng: pos[1]
                      }));
                      // Reverse geocoding
                      try {
                        const response = await fetch(
                          `https://nominatim.openstreetmap.org/reverse?format=json&lat=${pos[0]}&lon=${pos[1]}`,
                          { headers: { 'User-Agent': 'ImpoundPro/1.0' } }
                        );
                        const data = await response.json();
                        if (data.display_name) {
                          setEditJobData(prev => ({ ...prev, location_address: data.display_name }));
                        }
                      } catch (e) {
                        console.error('Reverse geocoding error:', e);
                      }
                    }}
                  />
                </MapContainer>
              </div>
              <p className="text-xs text-slate-500">Klicken Sie auf die Karte um den Standort zu ändern</p>
            </div>
          </div>
          <div className="flex justify-end gap-3">
            <Button variant="outline" onClick={() => setEditJobDialogOpen(false)}>
              Abbrechen
            </Button>
            <Button
              onClick={handleSaveJobData}
              disabled={editingJobData}
              className="bg-blue-600 hover:bg-blue-700"
            >
              {editingJobData ? 'Speichert...' : 'Speichern'}
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Authority Release Dialog */}
      <Dialog open={releaseDialogOpen} onOpenChange={setReleaseDialogOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <CheckCircle className="h-5 w-5 text-green-600" />
              Fahrzeug freigeben
            </DialogTitle>
            <DialogDescription>
              Geben Sie die Daten des Halters und die Zahlungsinformationen ein
            </DialogDescription>
          </DialogHeader>
          
          {selectedYardJob && (
            <div className="space-y-4">
              {/* Vehicle Info */}
              <div className="p-3 bg-slate-100 rounded-lg">
                <p className="font-bold">{selectedYardJob.license_plate}</p>
                <p className="text-sm text-slate-500">{selectedYardJob.job_number}</p>
              </div>

              {/* Owner Info */}
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <Label>Vorname *</Label>
                  <Input
                    value={releaseData.owner_first_name}
                    onChange={(e) => setReleaseData({...releaseData, owner_first_name: e.target.value})}
                    placeholder="Max"
                  />
                </div>
                <div className="space-y-1">
                  <Label>Nachname *</Label>
                  <Input
                    value={releaseData.owner_last_name}
                    onChange={(e) => setReleaseData({...releaseData, owner_last_name: e.target.value})}
                    placeholder="Mustermann"
                  />
                </div>
              </div>
              <div className="space-y-1">
                <Label>Adresse</Label>
                <Input
                  value={releaseData.owner_address}
                  onChange={(e) => setReleaseData({...releaseData, owner_address: e.target.value})}
                  placeholder="Musterstraße 1, 12345 Berlin"
                />
              </div>

              {/* Payment */}
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <Label>Zahlungsart *</Label>
                  <Select 
                    value={releaseData.payment_method} 
                    onValueChange={(value) => setReleaseData({...releaseData, payment_method: value})}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="bar">Bar</SelectItem>
                      <SelectItem value="karte">Karte</SelectItem>
                      <SelectItem value="rechnung">Rechnung</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-1">
                  <Label>Betrag (€) *</Label>
                  <Input
                    type="number"
                    step="0.01"
                    value={releaseData.payment_amount}
                    onChange={(e) => setReleaseData({...releaseData, payment_amount: e.target.value})}
                    placeholder="0.00"
                  />
                </div>
              </div>

              {/* Cost breakdown */}
              {selectedYardJob.authority_base_price && (
                <div className="p-3 bg-green-50 border border-green-200 rounded-lg">
                  <p className="font-medium text-green-800 mb-2">Kostenberechnung</p>
                  {calculateAuthorityCosts(selectedYardJob).breakdown.map((item, idx) => (
                    <div key={idx} className="flex justify-between text-sm">
                      <span>{item.label}</span>
                      <span>{item.amount.toFixed(2)} €</span>
                    </div>
                  ))}
                  <div className="flex justify-between font-bold text-green-800 border-t border-green-300 mt-2 pt-2">
                    <span>Gesamt:</span>
                    <span>{calculateAuthorityCosts(selectedYardJob).total.toFixed(2)} €</span>
                  </div>
                </div>
              )}

              {/* Service Invoice */}
              <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg">
                <Label className="text-blue-800">Rechnung an Abschleppdienst (€)</Label>
                <p className="text-xs text-blue-600 mb-2">
                  Dieser Betrag wird dem Abschleppdienst ({selectedYardJob.assigned_service_name}) als Rechnung gestellt
                </p>
                <Input
                  type="number"
                  step="0.01"
                  value={releaseData.service_invoice_amount}
                  onChange={(e) => setReleaseData({...releaseData, service_invoice_amount: e.target.value})}
                  placeholder="z.B. 150.00"
                />
              </div>

              <Button
                onClick={handleAuthorityRelease}
                disabled={releasingJob}
                className="w-full bg-green-500 hover:bg-green-600"
              >
                {releasingJob ? 'Wird freigegeben...' : 'Freigabe bestätigen & PDF erstellen'}
              </Button>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default AuthorityDashboard;
