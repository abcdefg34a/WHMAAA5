import React, { useState, useEffect, useRef } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useDeltaPolling } from '../hooks/useDeltaPolling';
import { useJobNotifications } from '../hooks/useJobNotifications';
import axios from 'axios';
import {
  Car, MapPin, Camera, LogOut, FileText, Copy, CheckCircle,
  Clock, Truck, Phone, Building2, Download, X, Settings, Euro,
  Filter, CheckSquare, Square, ChevronDown, Calendar, Plus, Search,
  Edit, Save, Undo2, User, Bell, BellOff, Volume2, VolumeX
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { VisuallyHidden } from '../components/ui/visually-hidden';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { RadioGroup, RadioGroupItem } from '../components/ui/radio-group';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { MapContainer, TileLayer, Marker, Popup, useMapEvents } from 'react-leaflet';
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

// Location Picker Component for Map
const LocationPicker = ({ position, setPosition }) => {
  useMapEvents({
    click(e) {
      setPosition([e.latlng.lat, e.latlng.lng]);
    },
  });

  return position ? <Marker position={position} /> : null;
};

// Map Click Handler for Edit Dialog
const MapClickHandler = ({ onMapClick }) => {
  useMapEvents({
    click(e) {
      onMapClick(e.latlng.lat, e.latlng.lng);
    },
  });
  return null;
};

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

        // Calculate new dimensions
        if (width > maxWidth) {
          height = Math.round((height * maxWidth) / width);
          width = maxWidth;
        }

        canvas.width = width;
        canvas.height = height;

        const ctx = canvas.getContext('2d');
        ctx.drawImage(img, 0, 0, width, height);

        // Convert to compressed JPEG
        const compressedDataUrl = canvas.toDataURL('image/jpeg', quality);
        resolve(compressedDataUrl);
      };
      img.src = event.target.result;
    };
    reader.readAsDataURL(file);
  });
};

export const TowingDashboard = () => {
  const { user, logout, updateUser } = useAuth();
  const [activeTab, setActiveTab] = useState('incoming');
  const [initialJobs, setInitialJobs] = useState([]);
  const { jobs, setJobs } = useDeltaPolling(initialJobs, user?.role);
  const [loading, setLoading] = useState(true);
  const [selectedJob, setSelectedJob] = useState(null);
  const [jobDetailOpen, setJobDetailOpen] = useState(false);
  const [releaseDialogOpen, setReleaseDialogOpen] = useState(false);
  
  // Echtzeit-Benachrichtigungen Hook
  const {
    notificationPermission,
    requestNotificationPermission,
    soundEnabled,
    setSoundEnabled,
    newJobsCount,
    clearNewJobsCount
  } = useJobNotifications(jobs, true);
  const [settingsDialogOpen, setSettingsDialogOpen] = useState(false);
  const [codeCopied, setCodeCopied] = useState(false);

  // Bulk selection state
  const [selectedJobIds, setSelectedJobIds] = useState([]);
  const [bulkUpdating, setBulkUpdating] = useState(false);

  // Filter state
  const [filterOpen, setFilterOpen] = useState(false);
  const [filterStatus, setFilterStatus] = useState('all');
  const [filterDateFrom, setFilterDateFrom] = useState('');
  const [filterDateTo, setFilterDateTo] = useState('');

  // NEW: Invoices state
  const [invoices, setInvoices] = useState([]);
  const [loadingInvoices, setLoadingInvoices] = useState(false);

  // Pagination state
  const [currentPage, setCurrentPage] = useState(1);
  const [totalJobs, setTotalJobs] = useState(0);
  const itemsPerPage = 50;

  // Release form state
  const [ownerFirstName, setOwnerFirstName] = useState('');
  const [ownerLastName, setOwnerLastName] = useState('');
  const [ownerAddress, setOwnerAddress] = useState('');
  const [paymentMethod, setPaymentMethod] = useState('cash');
  const [paymentAmount, setPaymentAmount] = useState('');
  const [serviceNotes, setServiceNotes] = useState('');
  const [servicePhotos, setServicePhotos] = useState([]);
  const fileInputRef = useRef(null);

  // Photo lightbox state
  const [lightboxOpen, setLightboxOpen] = useState(false);
  const [lightboxPhoto, setLightboxPhoto] = useState(null);
  const [lightboxIndex, setLightboxIndex] = useState(0);
  const [lightboxPhotos, setLightboxPhotos] = useState([]);

  // Settings state (costs)
  const [towCost, setTowCost] = useState(user?.tow_cost || 0);
  const [dailyCost, setDailyCost] = useState(user?.daily_cost || 0);
  const [savingCosts, setSavingCosts] = useState(false);

  // NEW: Extended pricing settings
  const [timeBasedEnabled, setTimeBasedEnabled] = useState(user?.time_based_enabled || false);
  const [firstHalfHour, setFirstHalfHour] = useState(user?.first_half_hour || '');
  const [additionalHalfHour, setAdditionalHalfHour] = useState(user?.additional_half_hour || '');
  const [processingFee, setProcessingFee] = useState(user?.processing_fee || '');
  const [emptyTripFee, setEmptyTripFee] = useState(user?.empty_trip_fee || '');
  const [nightSurcharge, setNightSurcharge] = useState(user?.night_surcharge || '');
  const [weekendSurcharge, setWeekendSurcharge] = useState(user?.weekend_surcharge || '');
  const [heavyVehicleSurcharge, setHeavyVehicleSurcharge] = useState(user?.heavy_vehicle_surcharge || '');
  
  // NEW: Weight Categories state
  const [weightCategories, setWeightCategories] = useState(user?.weight_categories || []);
  const [newWeightCategory, setNewWeightCategory] = useState({
    name: '',
    min_weight: '',
    max_weight: '',
    surcharge: '',
    is_default: false
  });

  // NEW: Company Info Dialog state
  const [companyInfoDialogOpen, setCompanyInfoDialogOpen] = useState(false);
  const [companyName, setCompanyName] = useState(user?.company_name || '');
  const [companyPhone, setCompanyPhone] = useState(user?.phone || '');
  const [companyEmail, setCompanyEmail] = useState(user?.email || '');
  const [companyYardAddress, setCompanyYardAddress] = useState(user?.yard_address || '');
  const [companyYardLat, setCompanyYardLat] = useState(user?.yard_lat || null);
  const [companyYardLng, setCompanyYardLng] = useState(user?.yard_lng || null);
  const [companyOpeningHours, setCompanyOpeningHours] = useState(user?.opening_hours || '');
  const [savingCompanyInfo, setSavingCompanyInfo] = useState(false);

  // NEW: Empty Trip (Leerfahrt) Dialog state
  const [emptyTripDialogOpen, setEmptyTripDialogOpen] = useState(false);
  const [emptyTripReason, setEmptyTripReason] = useState('vehicle_gone'); 
  // Reasons: 'vehicle_gone' (Auto nicht da), 'driver_present' (Halter aufgetaucht), 'driver_not_found' (Halter nicht aufgetaucht)
  const [emptyTripDriverFirstName, setEmptyTripDriverFirstName] = useState('');
  const [emptyTripDriverLastName, setEmptyTripDriverLastName] = useState('');
  const [emptyTripDriverAddress, setEmptyTripDriverAddress] = useState('');
  const [emptyTripPaymentMethod, setEmptyTripPaymentMethod] = useState('cash');
  const [emptyTripPaymentAmount, setEmptyTripPaymentAmount] = useState('');
  const [submittingEmptyTrip, setSubmittingEmptyTrip] = useState(false);

  // Cost calculation state
  const [calculatedCosts, setCalculatedCosts] = useState(null);
  const [loadingCosts, setLoadingCosts] = useState(false);

  // NEW: Create Job state
  const [createJobDialogOpen, setCreateJobDialogOpen] = useState(false);
  const [linkedAuthorities, setLinkedAuthorities] = useState([]);
  const [loadingAuthorities, setLoadingAuthorities] = useState(false);
  const [creatingJob, setCreatingJob] = useState(false);
  const [newJobPosition, setNewJobPosition] = useState(null); // Map position
  const [newJobData, setNewJobData] = useState({
    for_authority_id: '',
    license_plate: '',
    vin: '',
    tow_reason: '',
    location_address: '',
    location_lat: 52.52,
    location_lng: 13.405,
    notes: '',
    job_type: 'towing',
    // Sicherstellung fields
    sicherstellung_reason: '',
    vehicle_category: 'under_3_5t',
    ordering_authority: '',
    contact_attempts: false,
    contact_attempts_notes: '',
    estimated_vehicle_value: ''
  });
  const [newJobPhotos, setNewJobPhotos] = useState([]);
  const newJobFileInputRef = useRef(null);

  // NEW: Edit Job Data Dialog state
  const [editJobDialogOpen, setEditJobDialogOpen] = useState(false);
  const [editingJobData, setEditingJobData] = useState(false);
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
  const [deletingJob, setDeletingJob] = useState(false);

  useEffect(() => {
    fetchJobs();
  }, [filterStatus, filterDateFrom, filterDateTo, currentPage]);

  useEffect(() => {
    setTowCost(user?.tow_cost || 0);
    setDailyCost(user?.daily_cost || 0);
    setTimeBasedEnabled(user?.time_based_enabled || false);
    setFirstHalfHour(user?.first_half_hour || '');
    setAdditionalHalfHour(user?.additional_half_hour || '');
    setProcessingFee(user?.processing_fee || '');
    setEmptyTripFee(user?.empty_trip_fee || '');
    setNightSurcharge(user?.night_surcharge || '');
    setWeekendSurcharge(user?.weekend_surcharge || '');
    setHeavyVehicleSurcharge(user?.heavy_vehicle_surcharge || '');
    setWeightCategories(user?.weight_categories || []);
  }, [user]);

  // Clear selection when tab changes
  useEffect(() => {
    setSelectedJobIds([]);
  }, [activeTab]);

  // NEW: Fetch invoices
  const fetchInvoices = async () => {
    setLoadingInvoices(true);
    try {
      const response = await axios.get(`${API}/services/invoices`);
      setInvoices(response.data.invoices || []);
    } catch (error) {
      console.error('Error fetching invoices:', error);
    } finally {
      setLoadingInvoices(false);
    }
  };

  useEffect(() => {
    fetchInvoices();
  }, []);

  const fetchJobs = async () => {
    try {
      const params = new URLSearchParams();
      params.append('page', currentPage.toString());
      params.append('limit', itemsPerPage.toString());
      if (filterStatus && filterStatus !== 'all') {
        params.append('status', filterStatus);
      }
      if (filterDateFrom) {
        params.append('date_from', filterDateFrom);
      }
      if (filterDateTo) {
        params.append('date_to', filterDateTo);
      }

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

      const [jobsRes, countRes] = await Promise.all([
        axios.get(`${API}/jobs?${params.toString()}`),
        axios.get(`${API}/jobs/count/total?${countParams.toString()}`)
      ]);
      setInitialJobs(jobsRes.data);
      setTotalJobs(countRes.data.total);
    } catch (error) {
      console.error('Error fetching jobs:', error);
    } finally {
      setLoading(false);
    }
  };

  const handlePageChange = (page) => {
    setCurrentPage(page);
  };

  // Bulk selection handlers
  const toggleJobSelection = (jobId, event) => {
    event.stopPropagation();
    setSelectedJobIds(prev =>
      prev.includes(jobId)
        ? prev.filter(id => id !== jobId)
        : [...prev, jobId]
    );
  };

  const selectAllInTab = (tabJobs) => {
    const tabJobIds = tabJobs.map(j => j.id);
    const allSelected = tabJobIds.every(id => selectedJobIds.includes(id));
    if (allSelected) {
      setSelectedJobIds(prev => prev.filter(id => !tabJobIds.includes(id)));
    } else {
      setSelectedJobIds(prev => [...new Set([...prev, ...tabJobIds])]);
    }
  };

  const handleBulkStatusUpdate = async (newStatus) => {
    if (selectedJobIds.length === 0) return;

    setBulkUpdating(true);
    try {
      const response = await axios.post(`${API}/jobs/bulk-update-status`, {
        job_ids: selectedJobIds,
        status: newStatus
      });
      toast.success(response.data.message);
      setSelectedJobIds([]);
      fetchJobs();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Fehler bei der Massenaktualisierung');
    } finally {
      setBulkUpdating(false);
    }
  };

  const clearFilters = () => {
    setFilterStatus('all');
    setFilterDateFrom('');
    setFilterDateTo('');
    setCurrentPage(1);
  };

  const hasActiveFilters = filterStatus !== 'all' || filterDateFrom || filterDateTo;

  // NEW: Fetch linked authorities for job creation
  const fetchLinkedAuthorities = async () => {
    setLoadingAuthorities(true);
    try {
      const response = await axios.get(`${API}/towing/linked-authorities`);
      setLinkedAuthorities(response.data);
    } catch (error) {
      console.error('Error fetching linked authorities:', error);
      toast.error('Fehler beim Laden der verknüpften Behörden');
    } finally {
      setLoadingAuthorities(false);
    }
  };

  // NEW: Open create job dialog
  const openCreateJobDialog = () => {
    fetchLinkedAuthorities();
    setNewJobData({
      for_authority_id: '',
      license_plate: '',
      vin: '',
      tow_reason: '',
      location_address: '',
      location_lat: 52.52,
      location_lng: 13.405,
      notes: '',
      job_type: 'towing',
      sicherstellung_reason: '',
      vehicle_category: 'under_3_5t',
      ordering_authority: '',
      contact_attempts: false,
      contact_attempts_notes: '',
      estimated_vehicle_value: ''
    });
    setNewJobPhotos([]);
    setNewJobPosition(null);
    setCreateJobDialogOpen(true);
  };

  // NEW: Get current location for new job
  const handleGetNewJobLocation = () => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          const newPos = [pos.coords.latitude, pos.coords.longitude];
          setNewJobPosition(newPos);
          setNewJobData(prev => ({
            ...prev,
            location_lat: pos.coords.latitude,
            location_lng: pos.coords.longitude,
            location_address: `${pos.coords.latitude.toFixed(6)}, ${pos.coords.longitude.toFixed(6)}`
          }));
          toast.success('Standort erfasst!');
        },
        (error) => {
          toast.error('Standort konnte nicht ermittelt werden');
        }
      );
    } else {
      toast.error('Geolocation wird nicht unterstützt');
    }
  };

  // NEW: Handle map click for new job
  const handleNewJobMapClick = (pos) => {
    setNewJobPosition(pos);
    setNewJobData(prev => ({
      ...prev,
      location_lat: pos[0],
      location_lng: pos[1],
      location_address: `${pos[0].toFixed(6)}, ${pos[1].toFixed(6)}`
    }));
  };

  // NEW: Handle new job photo upload with compression
  const handleNewJobPhotoUpload = async (e) => {
    const files = Array.from(e.target.files);
    if (newJobPhotos.length + files.length > 5) {
      toast.error('Maximal 5 Fotos erlaubt');
      return;
    }

    toast.info('Fotos werden komprimiert...');

    for (const file of files) {
      try {
        const compressedImage = await compressImage(file, 1200, 0.7);
        setNewJobPhotos(prev => [...prev, compressedImage]);
      } catch (error) {
        console.error('Compression error:', error);
      }
    }
    toast.success('Fotos komprimiert und hinzugefügt');
  };

  // NEW: Remove photo from new job
  const removeNewJobPhoto = (index) => {
    setNewJobPhotos(prev => prev.filter((_, i) => i !== index));
  };

  // NEW: Create job as towing service
  const handleCreateJob = async () => {
    // Validation
    if (!newJobData.for_authority_id) {
      toast.error('Bitte wählen Sie eine Behörde aus');
      return;
    }
    if (!newJobData.license_plate && !newJobData.vin) {
      toast.error('Bitte geben Sie ein Kennzeichen oder eine FIN ein');
      return;
    }
    if (!newJobData.tow_reason) {
      toast.error('Bitte geben Sie einen Abschleppgrund ein');
      return;
    }
    if (!newJobData.location_address) {
      toast.error('Bitte geben Sie eine Adresse ein');
      return;
    }

    setCreatingJob(true);
    try {
      const payload = {
        ...newJobData,
        photos: newJobPhotos,
        estimated_vehicle_value: newJobData.estimated_vehicle_value ? parseFloat(newJobData.estimated_vehicle_value) : null
      };

      const idempotencyKey = crypto.randomUUID(); // Build-in browser capability

      await axios.post(`${API}/jobs`, payload, {
        headers: {
          'Idempotency-Key': idempotencyKey
        }
      });
      toast.success('Auftrag erfolgreich erstellt!');
      setCreateJobDialogOpen(false);
      fetchJobs();
    } catch (error) {
      console.error('Error creating job:', error);
      toast.error(error.response?.data?.detail || 'Fehler beim Erstellen des Auftrags');
    } finally {
      setCreatingJob(false);
    }
  };

  // NEW: Open Empty Trip Dialog
  const openEmptyTripDialog = () => {
    setEmptyTripReason('vehicle_gone');
    setEmptyTripDriverFirstName('');
    setEmptyTripDriverLastName('');
    setEmptyTripDriverAddress('');
    setEmptyTripPaymentMethod('cash');
    // Set default price from settings
    setEmptyTripPaymentAmount(user?.empty_trip_fee ? user.empty_trip_fee.toString() : '');
    setEmptyTripDialogOpen(true);
  };

  // NEW: Handle Empty Trip submission with PDF
  const handleEmptyTripSubmit = async () => {
    // Validation based on reason
    if (emptyTripReason === 'driver_present') {
      if (!emptyTripDriverFirstName || !emptyTripDriverLastName) {
        toast.error('Bitte geben Sie den Namen des Halters ein');
        return;
      }
    }
    
    // Allow 0€ for driver_not_found reason
    if (emptyTripReason !== 'driver_not_found' && !emptyTripPaymentAmount) {
      toast.error('Bitte geben Sie den Betrag ein');
      return;
    }

    setSubmittingEmptyTrip(true);
    try {
      // Build service notes based on reason
      let serviceNotes = '';
      const paymentAmount = parseFloat(emptyTripPaymentAmount) || 0;
      
      if (emptyTripReason === 'vehicle_gone') {
        serviceNotes = 'Leerfahrt - Fahrzeug war nicht mehr vor Ort';
      } else if (emptyTripReason === 'driver_present') {
        serviceNotes = `Leerfahrt - Halter vor Ort angetroffen: ${emptyTripDriverFirstName} ${emptyTripDriverLastName}`;
        if (emptyTripDriverAddress) {
          serviceNotes += `, Adresse: ${emptyTripDriverAddress}`;
        }
      } else if (emptyTripReason === 'driver_not_found') {
        serviceNotes = 'Leerfahrt - Halter nicht aufgetaucht, Fahrzeug nicht gefunden';
        if (paymentAmount === 0) {
          serviceNotes += ' - KOSTEN OFFEN - Behörde muss Halter kontaktieren';
        }
      }

      // Update job with empty trip data
      await axios.patch(`${API}/jobs/${selectedJob.id}`, {
        status: 'released',
        is_empty_trip: true,
        empty_trip_reason: emptyTripReason,
        service_notes: serviceNotes,
        owner_first_name: emptyTripReason === 'driver_present' ? emptyTripDriverFirstName : null,
        owner_last_name: emptyTripReason === 'driver_present' ? emptyTripDriverLastName : null,
        owner_address: emptyTripReason === 'driver_present' ? emptyTripDriverAddress : null,
        payment_method: paymentAmount > 0 ? emptyTripPaymentMethod : 'offen',
        payment_amount: paymentAmount
      });

      if (paymentAmount === 0 && emptyTripReason === 'driver_not_found') {
        toast.success('Leerfahrt erfasst! Kosten offen - Behörde wird benachrichtigt.');
      } else {
        toast.success('Leerfahrt erfasst!');
      }

      // Generate and download PDF
      const tokenRes = await axios.get(`${API}/jobs/${selectedJob.id}/pdf/token`);
      const pdfResponse = await axios.get(`${API}/jobs/${selectedJob.id}/pdf?token=${tokenRes.data.token}`, {
        responseType: 'blob'
      });
      const url = window.URL.createObjectURL(new Blob([pdfResponse.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `Leerfahrt_${selectedJob.job_number}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);

      setEmptyTripDialogOpen(false);
      setJobDetailOpen(false);
      fetchJobs();
    } catch (error) {
      console.error('Error processing empty trip:', error);
      toast.error('Fehler beim Erfassen der Leerfahrt');
    } finally {
      setSubmittingEmptyTrip(false);
    }
  };

  const copyServiceCode = async () => {
    if (user?.service_code) {
      try {
        await navigator.clipboard.writeText(user.service_code);
        setCodeCopied(true);
        toast.success('Code kopiert!');
        setTimeout(() => setCodeCopied(false), 2000);
      } catch (err) {
        // Fallback for browsers that don't support clipboard
        toast.info(`Ihr Code: ${user.service_code}`);
      }
    }
  };

  const handleSaveCosts = async () => {
    setSavingCosts(true);
    try {
      const response = await axios.patch(`${API}/services/pricing-settings`, {
        time_based_enabled: timeBasedEnabled,
        first_half_hour: parseFloat(firstHalfHour) || null,
        additional_half_hour: parseFloat(additionalHalfHour) || null,
        tow_cost: parseFloat(towCost) || null,
        daily_cost: parseFloat(dailyCost) || null,
        processing_fee: parseFloat(processingFee) || null,
        empty_trip_fee: parseFloat(emptyTripFee) || null,
        night_surcharge: parseFloat(nightSurcharge) || null,
        weekend_surcharge: parseFloat(weekendSurcharge) || null,
        heavy_vehicle_surcharge: parseFloat(heavyVehicleSurcharge) || null,
        weight_categories: weightCategories
      });
      updateUser(response.data);
      toast.success('Preiseinstellungen gespeichert!');
      setSettingsDialogOpen(false);
    } catch (error) {
      toast.error('Fehler beim Speichern');
    } finally {
      setSavingCosts(false);
    }
  };

  // NEW: Add weight category
  const handleAddWeightCategory = () => {
    if (!newWeightCategory.name.trim()) {
      toast.error('Bitte einen Namen eingeben');
      return;
    }
    
    const newCat = {
      id: crypto.randomUUID(),
      name: newWeightCategory.name.trim(),
      min_weight: newWeightCategory.min_weight ? parseFloat(newWeightCategory.min_weight) : null,
      max_weight: newWeightCategory.max_weight ? parseFloat(newWeightCategory.max_weight) : null,
      surcharge: parseFloat(newWeightCategory.surcharge) || 0,
      is_default: newWeightCategory.is_default
    };
    
    setWeightCategories([...weightCategories, newCat]);
    setNewWeightCategory({
      name: '',
      min_weight: '',
      max_weight: '',
      surcharge: '',
      is_default: false
    });
  };

  // NEW: Remove weight category
  const handleRemoveWeightCategory = (categoryId) => {
    setWeightCategories(weightCategories.filter(cat => cat.id !== categoryId));
  };

  // NEW: Open company info dialog
  const openCompanyInfoDialog = () => {
    setCompanyName(user?.company_name || '');
    setCompanyPhone(user?.phone || '');
    setCompanyEmail(user?.email || '');
    setCompanyYardAddress(user?.yard_address || '');
    setCompanyYardLat(user?.yard_lat || null);
    setCompanyYardLng(user?.yard_lng || null);
    setCompanyOpeningHours(user?.opening_hours || '');
    setCompanyInfoDialogOpen(true);
  };

  // NEW: Get current location for yard and reverse geocode
  const handleGetYardLocation = () => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        async (pos) => {
          setCompanyYardLat(pos.coords.latitude);
          setCompanyYardLng(pos.coords.longitude);

          try {
            const geocodeRes = await axios.get(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${pos.coords.latitude}&lon=${pos.coords.longitude}`);
            if (geocodeRes.data && geocodeRes.data.display_name) {
              setCompanyYardAddress(geocodeRes.data.display_name);
              toast.success('Standort & Adresse erfasst!');
            } else {
              toast.success('Hof-Standort erfasst!');
            }
          } catch (e) {
            console.error("Reverse geocoding error:", e);
            toast.success('Hof-Standort erfasst (Adresse konnte nicht ermittelt werden)');
          }
        },
        (error) => {
          toast.error('Standort konnte nicht ermittelt werden');
        }
      );
    } else {
      toast.error('Geolocation wird nicht unterstützt');
    }
  };

  // NEW: Save company info
  const handleSaveCompanyInfo = async () => {
    setSavingCompanyInfo(true);
    try {
      const response = await axios.patch(`${API}/towing/company-info`, {
        company_name: companyName || null,
        phone: companyPhone || null,
        email: companyEmail || null,
        yard_address: companyYardAddress || null,
        yard_lat: companyYardLat || null,
        yard_lng: companyYardLng || null,
        opening_hours: companyOpeningHours || null
      });
      updateUser(response.data);
      toast.success('Firmendaten gespeichert!');
      setCompanyInfoDialogOpen(false);
    } catch (error) {
      toast.error('Fehler beim Speichern');
    } finally {
      setSavingCompanyInfo(false);
    }
  };

  const fetchCalculatedCosts = async (jobId) => {
    setLoadingCosts(true);
    try {
      const response = await axios.get(`${API}/jobs/${jobId}/calculate-costs`);
      setCalculatedCosts(response.data);
      if (response.data.total > 0) {
        setPaymentAmount(response.data.total.toString());
      }
    } catch (error) {
      console.error('Error calculating costs:', error);
    } finally {
      setLoadingCosts(false);
    }
  };

  const handleStatusUpdate = async (jobId, newStatus) => {
    try {
      const updateData = { status: newStatus };
      if (serviceNotes) updateData.service_notes = serviceNotes;
      // WICHTIG: Sende auch die Service-Fotos mit
      if (servicePhotos && servicePhotos.length > 0) {
        updateData.service_photos = servicePhotos;
      }

      await axios.patch(`${API}/jobs/${jobId}`, updateData);
      toast.success('Status aktualisiert');
      fetchJobs();

      if (selectedJob?.id === jobId) {
        const response = await axios.get(`${API}/jobs/${jobId}`);
        setSelectedJob(response.data);
        // Aktualisiere auch die lokalen Fotos
        setServicePhotos(response.data.service_photos || []);
      }
    } catch (error) {
      toast.error('Fehler beim Aktualisieren');
    }
  };

  const handleReleaseVehicle = async () => {
    if (!selectedJob) return;

    if (!ownerFirstName || !ownerLastName || !paymentAmount) {
      toast.error('Bitte füllen Sie alle Pflichtfelder aus');
      return;
    }

    try {
      await axios.patch(`${API}/jobs/${selectedJob.id}`, {
        status: 'released',
        owner_first_name: ownerFirstName,
        owner_last_name: ownerLastName,
        owner_address: ownerAddress,
        payment_method: paymentMethod,
        payment_amount: parseFloat(paymentAmount)
      });

      toast.success('Fahrzeug als abgeholt markiert');
      setReleaseDialogOpen(false);
      setJobDetailOpen(false);
      resetReleaseForm();
      fetchJobs();

      // Download PDF
      downloadPDF(selectedJob.id, selectedJob.job_number);
    } catch (error) {
      toast.error('Fehler bei der Freigabe');
    }
  };

  const resetReleaseForm = () => {
    setOwnerFirstName('');
    setOwnerLastName('');
    setOwnerAddress('');
    setPaymentMethod('cash');
    setPaymentAmount('');
  };

  const handlePhotoUpload = async (e) => {
    const files = Array.from(e.target.files);
    toast.info('Fotos werden komprimiert...');

    for (const file of files) {
      try {
        const compressedImage = await compressImage(file, 1200, 0.7);
        setServicePhotos(prev => [...prev, compressedImage]);
      } catch (error) {
        console.error('Compression error:', error);
      }
    }
    toast.success('Fotos komprimiert');
  };

  // Photo Lightbox functions
  const openLightbox = (photos, index) => {
    setLightboxPhotos(photos);
    setLightboxIndex(index);
    setLightboxPhoto(photos[index]);
    setLightboxOpen(true);
  };

  const nextPhoto = () => {
    const newIndex = (lightboxIndex + 1) % lightboxPhotos.length;
    setLightboxIndex(newIndex);
    setLightboxPhoto(lightboxPhotos[newIndex]);
  };

  const prevPhoto = () => {
    const newIndex = (lightboxIndex - 1 + lightboxPhotos.length) % lightboxPhotos.length;
    setLightboxIndex(newIndex);
    setLightboxPhoto(lightboxPhotos[newIndex]);
  };

  const openJobDetail = (job) => {
    setSelectedJob(job);
    setServiceNotes(job.service_notes || '');
    // WICHTIG: Lade die vorhandenen Service-Fotos des Jobs, oder setze auf leer
    setServicePhotos(job.service_photos || []);
    setJobDetailOpen(true);
  };

  // NEW: Open edit dialog for job data
  const openEditJobDialog = (job) => {
    setEditJobData({
      license_plate: job.license_plate || '',
      vin: job.vin || '',
      tow_reason: job.tow_reason || '',
      notes: job.notes || '',
      location_address: job.location_address || '',
      location_lat: job.location_lat || null,
      location_lng: job.location_lng || null
    });
    // Set map position if coordinates exist
    if (job.location_lat && job.location_lng) {
      setEditJobPosition([job.location_lat, job.location_lng]);
    } else {
      setEditJobPosition(null);
    }
    setEditJobDialogOpen(true);
  };

  // NEW: Save edited job data
  const handleSaveJobData = async () => {
    if (!selectedJob) return;

    setEditingJobData(true);
    try {
      // Include coordinates if position was changed
      const dataToSend = {
        ...editJobData,
        location_lat: editJobPosition ? editJobPosition[0] : editJobData.location_lat,
        location_lng: editJobPosition ? editJobPosition[1] : editJobData.location_lng
      };

      const response = await axios.patch(`${API}/jobs/${selectedJob.id}/edit-data`, dataToSend);

      // Update local state
      setSelectedJob(response.data);
      setJobs(jobs.map(j => j.id === selectedJob.id ? response.data : j));

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
  const handleDeleteJob = async () => {
    if (!selectedJob) return;

    if (!window.confirm(`Auftrag ${selectedJob.job_number} wirklich löschen? Diese Aktion kann nicht rückgängig gemacht werden.`)) {
      return;
    }

    setDeletingJob(true);
    try {
      await axios.delete(`${API}/jobs/${selectedJob.id}`);

      // Remove from local state
      setJobs(jobs.filter(j => j.id !== selectedJob.id));
      setSelectedJob(null);
      setJobDetailOpen(false);

      toast.success(`Auftrag ${selectedJob.job_number} wurde gelöscht`);
    } catch (error) {
      console.error('Error deleting job:', error);
      toast.error(error.response?.data?.detail || 'Fehler beim Löschen des Auftrags');
    } finally {
      setDeletingJob(false);
    }
  };

  const getStatusBadge = (status, isEmptyTrip = false) => {
    if (isEmptyTrip) {
      return (
        <span className="px-2 py-1 rounded-full text-xs font-medium bg-orange-100 text-orange-800">
          Leerfahrt
        </span>
      );
    }
    const statusConfig = {
      pending: { label: 'Ausstehend', class: 'status-pending' },
      assigned: { label: 'Zugewiesen', class: 'status-assigned' },
      on_site: { label: 'Vor Ort', class: 'status-on_site' },
      towed: { label: 'Abgeschleppt', class: 'status-towed' },
      in_yard: { label: 'Im Hof', class: 'status-in_yard' },
      delivered_to_authority: { label: 'An Behörde übergeben', class: 'bg-purple-100 text-purple-800' },
      released: { label: 'Abgeholt', class: 'status-released' }
    };
    const config = statusConfig[status] || { label: status, class: 'bg-gray-500' };
    return (
      <span className={`px-2 py-1 rounded-full text-xs font-medium ${config.class}`}>
        {config.label}
      </span>
    );
  };

  // NEW: Helper to render yard type badge
  const getYardBadge = (job) => {
    if (job.target_yard === 'authority_yard') {
      return (
        <span className="px-2 py-0.5 text-xs font-medium bg-green-100 text-green-800 rounded-full flex items-center gap-1">
          <Building2 className="h-3 w-3" />
          Behörden-Hof
        </span>
      );
    }
    return null;
  };

  const filterJobs = (status) => {
    if (status === 'incoming') {
      return jobs.filter(j => ['assigned', 'on_site', 'towed'].includes(j.status));
    }
    if (status === 'in_yard') {
      // Include both in_yard and delivered_to_authority (completed authority yard jobs)
      return jobs.filter(j => j.status === 'in_yard' || j.status === 'delivered_to_authority');
    }
    if (status === 'released') {
      return jobs.filter(j => j.status === 'released');
    }
    return jobs;
  };

  const downloadPDF = async (jobId, jobNumber) => {
    try {
      const tokenRes = await axios.get(`${API}/jobs/${jobId}/pdf/token`);
      const response = await axios.get(`${API}/jobs/${jobId}/pdf?token=${tokenRes.data.token}`, {
        responseType: 'blob'
      });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `Abschleppprotokoll_${jobNumber || jobId}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('PDF download error:', error);
      toast.error('PDF konnte nicht heruntergeladen werden');
    }
  };

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center gap-3">
              <Truck className="h-8 w-8 text-slate-900" />
              <div className="hidden sm:block">
                <h1 className="font-bold text-lg text-slate-900" style={{ fontFamily: 'Chivo, sans-serif' }}>
                  Abschleppdienst
                </h1>
                <p className="text-xs text-slate-500">{user?.company_name}</p>
              </div>
            </div>

            <div className="flex items-center gap-3">
              {/* Service Code */}
              <div
                className="hidden md:flex items-center gap-2 bg-slate-100 px-3 py-2 rounded-lg cursor-pointer"
                onClick={copyServiceCode}
              >
                <span className="text-xs text-slate-500">Ihr Code:</span>
                <span className="font-mono font-bold text-slate-900">{user?.service_code}</span>
                {codeCopied ? (
                  <CheckCircle className="h-4 w-4 text-green-500" />
                ) : (
                  <Copy className="h-4 w-4 text-slate-400" />
                )}
              </div>

              {/* Settings Button */}
              <Button
                data-testid="settings-btn"
                variant="outline"
                size="sm"
                onClick={() => setSettingsDialogOpen(true)}
                title="Preise anpassen"
              >
                <Euro className="h-4 w-4" />
              </Button>

              {/* Company Info Button */}
              <Button
                data-testid="company-info-btn"
                variant="outline"
                size="sm"
                onClick={openCompanyInfoDialog}
                title="Firmendaten bearbeiten"
              >
                <Building2 className="h-4 w-4" />
              </Button>

              {/* Notification Settings */}
              <div className="flex items-center gap-1 border rounded-md px-2 py-1 bg-slate-50">
                {/* Notification Permission Button */}
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={async () => {
                    if (notificationPermission !== 'granted') {
                      const granted = await requestNotificationPermission();
                      if (granted) {
                        toast.success('🔔 Benachrichtigungen aktiviert!');
                      }
                    }
                  }}
                  className={`relative p-1 h-8 w-8 ${notificationPermission === 'granted' ? 'text-green-600' : 'text-slate-400'}`}
                  title={notificationPermission === 'granted' ? 'Benachrichtigungen aktiv' : 'Benachrichtigungen aktivieren'}
                >
                  {notificationPermission === 'granted' ? (
                    <Bell className="h-4 w-4" />
                  ) : (
                    <BellOff className="h-4 w-4" />
                  )}
                  {newJobsCount > 0 && (
                    <span className="absolute -top-1 -right-1 bg-red-500 text-white text-xs rounded-full h-5 w-5 flex items-center justify-center animate-pulse">
                      {newJobsCount > 9 ? '9+' : newJobsCount}
                    </span>
                  )}
                </Button>
                
                {/* Sound Toggle */}
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setSoundEnabled(!soundEnabled)}
                  className={`p-1 h-8 w-8 ${soundEnabled ? 'text-green-600' : 'text-slate-400'}`}
                  title={soundEnabled ? 'Ton an' : 'Ton aus'}
                >
                  {soundEnabled ? (
                    <Volume2 className="h-4 w-4" />
                  ) : (
                    <VolumeX className="h-4 w-4" />
                  )}
                </Button>
              </div>

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
        {/* NEW: New Jobs Alert Banner */}
        {newJobsCount > 0 && (
          <div className="mb-6 bg-gradient-to-r from-amber-500 to-orange-500 text-white rounded-lg shadow-lg overflow-hidden animate-pulse">
            <div className="px-6 py-4 flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="bg-white/20 rounded-full p-3">
                  <Bell className="h-8 w-8 animate-bounce" />
                </div>
                <div>
                  <h3 className="text-xl font-bold">
                    🚨 {newJobsCount} neue{newJobsCount > 1 ? ' Aufträge' : 'r Auftrag'}!
                  </h3>
                  <p className="text-amber-100">
                    Sie haben neue Abschleppaufträge erhalten. Bitte prüfen Sie diese.
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <Button 
                  onClick={() => {
                    setActiveTab('incoming');
                    clearNewJobsCount();
                  }}
                  className="bg-white text-orange-600 hover:bg-orange-100 font-bold"
                >
                  Jetzt ansehen
                </Button>
                <Button 
                  variant="ghost" 
                  onClick={clearNewJobsCount}
                  className="text-white hover:bg-white/20"
                >
                  <X className="h-5 w-5" />
                </Button>
              </div>
            </div>
          </div>
        )}

        {/* Notification Permission Banner */}
        {notificationPermission === 'default' && (
          <div className="mb-6 bg-blue-50 border border-blue-200 rounded-lg px-6 py-4 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Bell className="h-6 w-6 text-blue-600" />
              <div>
                <p className="font-semibold text-blue-900">Benachrichtigungen aktivieren</p>
                <p className="text-sm text-blue-700">Erhalten Sie sofort einen Alarm wenn neue Aufträge eingehen.</p>
              </div>
            </div>
            <Button 
              onClick={async () => {
                const granted = await requestNotificationPermission();
                if (granted) {
                  toast.success('🔔 Benachrichtigungen aktiviert!');
                }
              }}
              className="bg-blue-600 hover:bg-blue-700"
            >
              Aktivieren
            </Button>
          </div>
        )}

        {/* Company Info Card */}
        <Card className="mb-6 border-blue-200 bg-blue-50">
          <CardContent className="py-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <Building2 className="h-6 w-6 text-blue-600" />
                <div>
                  <p className="text-sm text-blue-700">Ihre Firmendaten</p>
                  <p className="font-bold text-blue-900">
                    {user?.company_name || 'Nicht angegeben'} | {user?.phone || 'Keine Telefonnummer'}
                  </p>
                  <p className="text-xs text-blue-600">
                    Hof: {user?.yard_address || 'Keine Adresse hinterlegt'}
                  </p>
                </div>
              </div>
              <Button variant="outline" size="sm" onClick={openCompanyInfoDialog} className="border-blue-300 text-blue-700 hover:bg-blue-100">
                Bearbeiten
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Service Code Card (Mobile) */}
        <Card className="mb-6 md:hidden">
          <CardContent className="py-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-slate-500">Ihr Verknüpfungscode</p>
                <p className="font-mono font-bold text-2xl text-slate-900">{user?.service_code}</p>
              </div>
              <Button variant="outline" onClick={copyServiceCode}>
                {codeCopied ? <CheckCircle className="h-5 w-5" /> : <Copy className="h-5 w-5" />}
              </Button>
            </div>
            <p className="text-xs text-slate-500 mt-2">
              Geben Sie diesen Code an Behörden weiter, um Aufträge zu erhalten
            </p>
          </CardContent>
        </Card>

        {/* Cost Info Card */}
        <Card className="mb-6 border-orange-200 bg-orange-50">
          <CardContent className="py-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <Euro className="h-6 w-6 text-orange-600" />
                <div>
                  <p className="text-sm text-orange-700">Ihre Preise</p>
                  <p className="font-bold text-orange-900">
                    Anfahrt: {(user?.tow_cost || 0).toFixed(2)} € | Standkosten: {(user?.daily_cost || 0).toFixed(2)} €/Tag
                  </p>
                </div>
              </div>
              <Button variant="outline" size="sm" onClick={() => setSettingsDialogOpen(true)}>
                Anpassen
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* NEW: Create Job Card */}
        <Card className="mb-6 border-green-200 bg-green-50">
          <CardContent className="py-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <Car className="h-6 w-6 text-green-600" />
                <div>
                  <p className="text-sm text-green-700">Eigenen Auftrag erstellen</p>
                  <p className="font-bold text-green-900">
                    Erstellen Sie selbst einen Auftrag für eine verknüpfte Behörde
                  </p>
                </div>
              </div>
              <Button
                className="bg-green-600 hover:bg-green-700 text-white"
                onClick={openCreateJobDialog}
              >
                + Neuer Auftrag
              </Button>
            </div>
          </CardContent>
        </Card>

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
            </div>

            {filterOpen && (
              <div className="mt-4 pt-4 border-t grid sm:grid-cols-3 gap-4">
                <div className="space-y-2">
                  <Label className="text-sm text-slate-500">Status</Label>
                  <Select value={filterStatus} onValueChange={setFilterStatus}>
                    <SelectTrigger>
                      <SelectValue placeholder="Alle Status" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">Alle Status</SelectItem>
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
                  <Label className="text-sm text-slate-500">Datum von</Label>
                  <Input
                    type="date"
                    value={filterDateFrom}
                    onChange={(e) => setFilterDateFrom(e.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label className="text-sm text-slate-500">Datum bis</Label>
                  <Input
                    type="date"
                    value={filterDateTo}
                    onChange={(e) => setFilterDateTo(e.target.value)}
                  />
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Bulk Action Bar - appears when items selected */}
        {selectedJobIds.length > 0 && (
          <Card className="mb-6 border-blue-200 bg-blue-50">
            <CardContent className="py-3">
              <div className="flex flex-wrap items-center justify-between gap-4">
                <div className="flex items-center gap-2">
                  <CheckSquare className="h-5 w-5 text-blue-600" />
                  <span className="font-medium text-blue-800">
                    {selectedJobIds.length} Auftrag{selectedJobIds.length > 1 ? 'e' : ''} ausgewählt
                  </span>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-sm text-blue-700 mr-2">Status ändern:</span>
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={bulkUpdating}
                    onClick={() => handleBulkStatusUpdate('on_site')}
                    className="bg-orange-100 border-orange-300 text-orange-700 hover:bg-orange-200"
                  >
                    Vor Ort
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={bulkUpdating}
                    onClick={() => handleBulkStatusUpdate('towed')}
                    className="bg-red-100 border-red-300 text-red-700 hover:bg-red-200"
                  >
                    Abgeschleppt
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={bulkUpdating}
                    onClick={() => handleBulkStatusUpdate('in_yard')}
                    className="bg-yellow-100 border-yellow-300 text-yellow-700 hover:bg-yellow-200"
                  >
                    Im Hof
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => setSelectedJobIds([])}
                    className="text-slate-500"
                  >
                    <X className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="mb-6">
            <TabsTrigger data-testid="tab-incoming" value="incoming" className="flex items-center gap-2">
              <Truck className="h-4 w-4" />
              Eingehend ({filterJobs('incoming').length})
            </TabsTrigger>
            <TabsTrigger data-testid="tab-in-yard" value="in_yard" className="flex items-center gap-2">
              <Building2 className="h-4 w-4" />
              Im Hof ({filterJobs('in_yard').length})
            </TabsTrigger>
            <TabsTrigger data-testid="tab-released" value="released" className="flex items-center gap-2">
              <CheckCircle className="h-4 w-4" />
              Abgeholt ({filterJobs('released').length})
            </TabsTrigger>
            <TabsTrigger data-testid="tab-invoices" value="invoices" className="flex items-center gap-2">
              <FileText className="h-4 w-4" />
              Rechnungen ({invoices.filter(i => i.status === 'pending').length})
            </TabsTrigger>
          </TabsList>

          {/* Incoming Jobs */}
          <TabsContent value="incoming">
            {loading ? (
              <div className="flex justify-center py-8">
                <div className="loading-spinner"></div>
              </div>
            ) : filterJobs('incoming').length === 0 ? (
              <div className="empty-state">
                <Truck className="empty-state-icon" />
                <p>Keine eingehenden Aufträge</p>
              </div>
            ) : (
              <>
                {/* Select All for Incoming */}
                <div className="mb-4 flex items-center gap-2">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => selectAllInTab(filterJobs('incoming'))}
                    className="text-slate-600"
                  >
                    {filterJobs('incoming').every(j => selectedJobIds.includes(j.id)) ? (
                      <><CheckSquare className="h-4 w-4 mr-2" /> Alle abwählen</>
                    ) : (
                      <><Square className="h-4 w-4 mr-2" /> Alle auswählen</>
                    )}
                  </Button>
                </div>
                <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {filterJobs('incoming').map(job => (
                    <Card
                      key={job.id}
                      className={`cursor-pointer hover:shadow-lg transition-shadow relative ${selectedJobIds.includes(job.id) ? 'ring-2 ring-blue-500 bg-blue-50' : ''
                        }`}
                      onClick={() => openJobDetail(job)}
                    >
                      {/* Checkbox */}
                      <button
                        className="absolute top-2 right-2 z-10 p-1 rounded hover:bg-slate-100"
                        onClick={(e) => toggleJobSelection(job.id, e)}
                      >
                        {selectedJobIds.includes(job.id) ? (
                          <CheckSquare className="h-5 w-5 text-blue-600" />
                        ) : (
                          <Square className="h-5 w-5 text-slate-400" />
                        )}
                      </button>
                      <CardContent className="p-4 pr-10">
                        <div className="flex justify-between items-start mb-3">
                          <div>
                            <div className="flex items-center gap-2 flex-wrap">
                              <p className="job-license-plate">{job.license_plate}</p>
                              {getYardBadge(job)}
                            </div>
                            <p className="text-xs text-slate-500">{job.job_number}</p>
                          </div>
                          {getStatusBadge(job.status, job.is_empty_trip)}
                        </div>
                        <div className="space-y-2 text-sm">
                          <div className="flex items-center gap-2 text-slate-600">
                            <MapPin className="h-4 w-4 flex-shrink-0" />
                            <span className="truncate">{job.location_address}</span>
                          </div>
                          <div className="flex items-center gap-2 text-slate-600">
                            <Clock className="h-4 w-4" />
                            <span>{new Date(job.created_at).toLocaleString('de-DE')}</span>
                          </div>
                          {/* Show authority yard destination */}
                          {job.target_yard === 'authority_yard' && job.authority_yard_address && (
                            <div className="flex items-center gap-2 text-green-700 bg-green-50 p-1 rounded">
                              <Building2 className="h-4 w-4 flex-shrink-0" />
                              <span className="truncate text-xs">Ziel: {job.authority_yard_address}</span>
                            </div>
                          )}
                        </div>
                        <p className="mt-2 text-sm font-medium text-orange-600">
                          {job.tow_reason}
                        </p>
                        {/* Show job type and sicherstellung details */}
                        {job.job_type === 'sicherstellung' && (
                          <div className="mt-2 p-2 bg-amber-50 border border-amber-200 rounded text-xs">
                            <span className="font-semibold text-amber-800">Sicherstellung</span>
                            {job.sicherstellung_reason && (
                              <span className="text-amber-700"> • {
                                {
                                  'betriebsmittel': 'Betriebsmittel',
                                  'gestohlen': 'Gestohlen/Fahndung',
                                  'eigentumssicherung': 'Eigentumssicherung',
                                  'technische_maengel': 'Techn. Mängel',
                                  'strafrechtlich': 'Strafrechtlich'
                                }[job.sicherstellung_reason] || job.sicherstellung_reason
                              }</span>
                            )}
                            {job.vehicle_category === 'over_3_5t' && (
                              <span className="text-amber-700"> • ab 3,5t</span>
                            )}
                          </div>
                        )}
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </>
            )}
          </TabsContent>

          {/* In Yard */}
          <TabsContent value="in_yard">
            {filterJobs('in_yard').length === 0 ? (
              <div className="empty-state">
                <Building2 className="empty-state-icon" />
                <p>Keine Fahrzeuge im Hof</p>
              </div>
            ) : (
              <>
                {/* Select All for In Yard */}
                <div className="mb-4 flex items-center gap-2">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => selectAllInTab(filterJobs('in_yard'))}
                    className="text-slate-600"
                  >
                    {filterJobs('in_yard').every(j => selectedJobIds.includes(j.id)) ? (
                      <><CheckSquare className="h-4 w-4 mr-2" /> Alle abwählen</>
                    ) : (
                      <><Square className="h-4 w-4 mr-2" /> Alle auswählen</>
                    )}
                  </Button>
                </div>
                <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {filterJobs('in_yard').map(job => (
                    <Card
                      key={job.id}
                      className={`cursor-pointer hover:shadow-lg transition-shadow relative ${selectedJobIds.includes(job.id) ? 'ring-2 ring-blue-500 bg-blue-50' : ''
                        }`}
                      onClick={() => openJobDetail(job)}
                    >
                      {/* Checkbox */}
                      <button
                        className="absolute top-2 right-2 z-10 p-1 rounded hover:bg-slate-100"
                        onClick={(e) => toggleJobSelection(job.id, e)}
                      >
                        {selectedJobIds.includes(job.id) ? (
                          <CheckSquare className="h-5 w-5 text-blue-600" />
                        ) : (
                          <Square className="h-5 w-5 text-slate-400" />
                        )}
                      </button>
                      <CardContent className="p-4 pr-10">
                        <div className="flex justify-between items-start mb-3">
                          <div>
                            <div className="flex items-center gap-2 flex-wrap">
                              <p className="job-license-plate">{job.license_plate}</p>
                              {getYardBadge(job)}
                            </div>
                            <p className="text-xs text-slate-500">{job.job_number}</p>
                          </div>
                          {getStatusBadge(job.status, job.is_empty_trip)}
                        </div>
                        <div className="space-y-2 text-sm text-slate-600">
                          <p>Im Hof seit: {job.in_yard_at || job.delivered_to_authority_at ? new Date(job.delivered_to_authority_at || job.in_yard_at).toLocaleString('de-DE') : '-'}</p>
                          {job.vin && <p>FIN: {job.vin}</p>}
                          {job.target_yard === 'authority_yard' && (
                            <p className="text-green-700 text-xs">✓ An Behörde übergeben</p>
                          )}
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </>
            )}
          </TabsContent>

          {/* Released */}
          <TabsContent value="released">
            {filterJobs('released').length === 0 ? (
              <div className="empty-state">
                <CheckCircle className="empty-state-icon" />
                <p>Keine abgeholten Fahrzeuge</p>
              </div>
            ) : (
              <div className="space-y-3">
                {filterJobs('released').map(job => (
                  <Card key={job.id}>
                    <CardContent className="p-4">
                      <div className="flex flex-wrap justify-between items-start gap-4">
                        <div>
                          <div className="flex items-center gap-2 flex-wrap">
                            <p className="job-license-plate">{job.license_plate}</p>
                            {getYardBadge(job)}
                          </div>
                          <p className="text-xs text-slate-500">{job.job_number}</p>
                          <p className="text-sm text-slate-600 mt-1">
                            Abgeholt von: {job.owner_first_name} {job.owner_last_name}
                          </p>
                          <p className="text-sm text-slate-600">
                            Zahlung: {job.payment_amount?.toFixed(2)} € ({job.payment_method === 'cash' ? 'Bar' : job.payment_method === 'offen' ? 'Offen' : 'Karte'})
                          </p>
                        </div>
                        <Button
                          variant="outline"
                          onClick={() => downloadPDF(job.id, job.job_number)}
                          className="flex items-center gap-2"
                        >
                          <Download className="h-4 w-4" />
                          PDF
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </TabsContent>

          {/* Invoices Tab */}
          <TabsContent value="invoices">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <FileText className="h-5 w-5" />
                  Rechnungen von Behörden
                </CardTitle>
                <CardDescription>
                  Rechnungen für Aufträge, die auf Behörden-Höfe geliefert wurden
                </CardDescription>
              </CardHeader>
              <CardContent>
                {loadingInvoices ? (
                  <div className="flex justify-center py-8">
                    <div className="loading-spinner"></div>
                  </div>
                ) : invoices.length === 0 ? (
                  <div className="text-center py-8 text-slate-500">
                    <FileText className="h-12 w-12 mx-auto mb-4 opacity-30" />
                    <p>Keine Rechnungen vorhanden</p>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {/* Pending Invoices */}
                    {invoices.filter(i => i.status === 'pending').length > 0 && (
                      <div>
                        <h4 className="font-semibold text-amber-700 mb-3">⏳ Offene Rechnungen</h4>
                        <div className="space-y-2">
                          {invoices.filter(i => i.status === 'pending').map(invoice => (
                            <div key={invoice.id} className="flex items-center justify-between p-4 bg-amber-50 border border-amber-200 rounded-lg">
                              <div>
                                <p className="font-medium">{invoice.license_plate}</p>
                                <p className="text-sm text-slate-500">{invoice.job_number}</p>
                                <p className="text-sm text-slate-500">Von: {invoice.authority_name}</p>
                                <p className="text-xs text-slate-400">
                                  {invoice.created_at ? new Date(invoice.created_at).toLocaleString('de-DE') : '-'}
                                </p>
                              </div>
                              <div className="text-right flex flex-col items-end gap-2">
                                <p className="text-2xl font-bold text-amber-600">{invoice.amount?.toFixed(2)} €</p>
                                <span className="text-xs px-2 py-1 bg-amber-100 text-amber-800 rounded-full">Offen</span>
                                <Button
                                  size="sm"
                                  variant="outline"
                                  className="text-green-700 border-green-300 hover:bg-green-50"
                                  onClick={async () => {
                                    if (window.confirm(`Rechnung für ${invoice.license_plate} (${invoice.amount?.toFixed(2)} €) als bezahlt markieren?`)) {
                                      try {
                                        await axios.patch(`${API}/services/invoices/${invoice.id}/mark-paid`);
                                        fetchInvoices();
                                        alert('Rechnung als bezahlt markiert!');
                                      } catch (error) {
                                        console.error('Error marking invoice paid:', error);
                                        alert(error.response?.data?.detail || 'Fehler beim Markieren der Rechnung');
                                      }
                                    }
                                  }}
                                >
                                  <CheckCircle className="h-4 w-4 mr-1" />
                                  Als bezahlt markieren
                                </Button>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Paid Invoices */}
                    {invoices.filter(i => i.status === 'paid').length > 0 && (
                      <div>
                        <h4 className="font-semibold text-green-700 mb-3">✅ Bezahlte Rechnungen</h4>
                        <div className="space-y-2">
                          {invoices.filter(i => i.status === 'paid').map(invoice => (
                            <div key={invoice.id} className="flex items-center justify-between p-4 bg-green-50 border border-green-200 rounded-lg">
                              <div>
                                <p className="font-medium">{invoice.license_plate}</p>
                                <p className="text-sm text-slate-500">{invoice.job_number}</p>
                                <p className="text-sm text-slate-500">Von: {invoice.authority_name}</p>
                              </div>
                              <div className="text-right">
                                <p className="text-xl font-bold text-green-600">{invoice.amount?.toFixed(2)} €</p>
                                <span className="text-xs px-2 py-1 bg-green-100 text-green-800 rounded-full">Bezahlt</span>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Summary */}
                    <div className="mt-6 p-4 bg-slate-100 rounded-lg">
                      <div className="flex justify-between items-center">
                        <span className="font-medium">Offene Summe:</span>
                        <span className="text-xl font-bold text-amber-600">
                          {invoices.filter(i => i.status === 'pending').reduce((sum, i) => sum + (i.amount || 0), 0).toFixed(2)} €
                        </span>
                      </div>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* Profile Tab */}
          <TabsContent value="profile">
            <TwoFactorSetup />
          </TabsContent>
        </Tabs>

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
      </main>

      {/* Settings Dialog (Costs) */}
      <Dialog open={settingsDialogOpen} onOpenChange={setSettingsDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Euro className="h-5 w-5" />
              Preiseinstellungen
            </DialogTitle>
            <DialogDescription>
              Konfigurieren Sie Ihre Preise - nur ausgefüllte Felder werden berechnet
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-6 py-4">
            {/* Zeitbasierte Berechnung */}
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="font-semibold">Zeitbasierte Berechnung</h4>
                  <p className="text-xs text-slate-500">Für Sicherstellungen nach Berliner Gebührenordnung</p>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={timeBasedEnabled}
                    onChange={(e) => setTimeBasedEnabled(e.target.checked)}
                    className="sr-only peer"
                  />
                  <div className="w-11 h-6 bg-slate-200 peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                </label>
              </div>

              {timeBasedEnabled && (
                <div className="grid grid-cols-2 gap-4 p-4 bg-blue-50 rounded-lg">
                  <div className="space-y-2">
                    <Label>Erste halbe Stunde (€)</Label>
                    <Input
                      type="number"
                      step="0.01"
                      min="0"
                      value={firstHalfHour}
                      onChange={(e) => setFirstHalfHour(e.target.value)}
                      placeholder="137.00"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Jede weitere halbe Stunde (€)</Label>
                    <Input
                      type="number"
                      step="0.01"
                      min="0"
                      value={additionalHalfHour}
                      onChange={(e) => setAdditionalHalfHour(e.target.value)}
                      placeholder="93.00"
                    />
                  </div>
                </div>
              )}
            </div>

            {/* Standard Preise */}
            <div className="space-y-4">
              <h4 className="font-semibold">Standard Preise</h4>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Anfahrt/Abschleppen (€)</Label>
                  <Input
                    type="number"
                    step="0.01"
                    min="0"
                    value={towCost}
                    onChange={(e) => setTowCost(e.target.value)}
                    placeholder="150.00"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Standkosten pro Tag (€)</Label>
                  <Input
                    type="number"
                    step="0.01"
                    min="0"
                    value={dailyCost}
                    onChange={(e) => setDailyCost(e.target.value)}
                    placeholder="20.00"
                  />
                </div>
              </div>
            </div>

            {/* Zusatzkosten */}
            <div className="space-y-4">
              <h4 className="font-semibold">Zusatzkosten (optional)</h4>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Bearbeitungsgebühr (€)</Label>
                  <Input
                    type="number"
                    step="0.01"
                    min="0"
                    value={processingFee}
                    onChange={(e) => setProcessingFee(e.target.value)}
                    placeholder="63.00"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Leerfahrt (€)</Label>
                  <Input
                    type="number"
                    step="0.01"
                    min="0"
                    value={emptyTripFee}
                    onChange={(e) => setEmptyTripFee(e.target.value)}
                    placeholder="31.50"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Nachtzuschlag (€)</Label>
                  <Input
                    type="number"
                    step="0.01"
                    min="0"
                    value={nightSurcharge}
                    onChange={(e) => setNightSurcharge(e.target.value)}
                    placeholder="0.00"
                  />
                  <p className="text-xs text-slate-500">22:00 - 06:00 Uhr</p>
                </div>
                <div className="space-y-2">
                  <Label>Wochenendzuschlag (€)</Label>
                  <Input
                    type="number"
                    step="0.01"
                    min="0"
                    value={weekendSurcharge}
                    onChange={(e) => setWeekendSurcharge(e.target.value)}
                    placeholder="0.00"
                  />
                  <p className="text-xs text-slate-500">Samstag & Sonntag</p>
                </div>
              </div>
            </div>

            {/* NEW: Gewichtskategorien */}
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="font-semibold">Gewichtskategorien</h4>
                  <p className="text-xs text-slate-500">Definieren Sie flexible Zuschläge nach Fahrzeuggewicht</p>
                </div>
              </div>
              
              {/* Liste der vorhandenen Kategorien */}
              {weightCategories.length > 0 && (
                <div className="space-y-2">
                  {weightCategories.map((cat) => (
                    <div key={cat.id} className="flex items-center justify-between p-3 bg-slate-50 rounded-lg border">
                      <div>
                        <span className="font-medium">{cat.name}</span>
                        <span className="text-sm text-slate-500 ml-2">
                          {cat.min_weight != null && cat.max_weight != null ? (
                            `(${cat.min_weight}t - ${cat.max_weight}t)`
                          ) : cat.min_weight != null ? (
                            `(ab ${cat.min_weight}t)`
                          ) : cat.max_weight != null ? (
                            `(bis ${cat.max_weight}t)`
                          ) : (
                            '(alle Gewichte)'
                          )}
                        </span>
                      </div>
                      <div className="flex items-center gap-3">
                        <span className="font-bold text-green-600">
                          {cat.surcharge > 0 ? `+${cat.surcharge.toFixed(2)} €` : 'Kein Zuschlag'}
                        </span>
                        <button
                          type="button"
                          onClick={() => handleRemoveWeightCategory(cat.id)}
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
                <div className="grid grid-cols-2 gap-3">
                  <div className="col-span-2">
                    <Input
                      placeholder="Name (z.B. 'LKW 3,5-7,5t')"
                      value={newWeightCategory.name}
                      onChange={(e) => setNewWeightCategory({...newWeightCategory, name: e.target.value})}
                    />
                  </div>
                  <div>
                    <Input
                      type="number"
                      step="0.1"
                      min="0"
                      placeholder="Von (t) - leer = kein Minimum"
                      value={newWeightCategory.min_weight}
                      onChange={(e) => setNewWeightCategory({...newWeightCategory, min_weight: e.target.value})}
                    />
                  </div>
                  <div>
                    <Input
                      type="number"
                      step="0.1"
                      min="0"
                      placeholder="Bis (t) - leer = kein Maximum"
                      value={newWeightCategory.max_weight}
                      onChange={(e) => setNewWeightCategory({...newWeightCategory, max_weight: e.target.value})}
                    />
                  </div>
                  <div className="col-span-2">
                    <Input
                      type="number"
                      step="0.01"
                      min="0"
                      placeholder="Zuschlag in € (0 = kein Zuschlag)"
                      value={newWeightCategory.surcharge}
                      onChange={(e) => setNewWeightCategory({...newWeightCategory, surcharge: e.target.value})}
                    />
                  </div>
                </div>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={handleAddWeightCategory}
                  className="w-full"
                >
                  <Plus className="h-4 w-4 mr-2" />
                  Kategorie hinzufügen
                </Button>
              </div>

              {/* Alt: Fester Schwerlastzuschlag (wird ausgeblendet wenn Kategorien existieren) */}
              {weightCategories.length === 0 && (
                <div className="space-y-2 p-3 bg-amber-50 rounded-lg border border-amber-200">
                  <p className="text-xs text-amber-700">Alternativ: Fester Schwerlastzuschlag (ab 3,5t)</p>
                  <Input
                    type="number"
                    step="0.01"
                    min="0"
                    value={heavyVehicleSurcharge}
                    onChange={(e) => setHeavyVehicleSurcharge(e.target.value)}
                    placeholder="0.00"
                  />
                </div>
              )}
            </div>

            {/* Beispielrechnung */}
            <div className="bg-slate-50 rounded-lg p-4">
              <p className="text-sm font-medium text-slate-700">Beispielrechnung (Standard)</p>
              <p className="text-sm text-slate-600 mt-1">
                Fahrzeug 3 Tage im Hof: {parseFloat(towCost || 0).toFixed(2)} € + (3 × {parseFloat(dailyCost || 0).toFixed(2)} €)
                {processingFee ? ` + ${parseFloat(processingFee).toFixed(2)} € Bearbeitung` : ''}
                = <span className="font-bold">{(parseFloat(towCost || 0) + 3 * parseFloat(dailyCost || 0) + parseFloat(processingFee || 0)).toFixed(2)} €</span>
              </p>
            </div>

            <Button
              data-testid="save-costs-btn"
              onClick={handleSaveCosts}
              disabled={savingCosts}
              className="w-full bg-slate-900 hover:bg-slate-800"
            >
              {savingCosts ? <div className="loading-spinner mr-2"></div> : null}
              Speichern
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Job Detail Dialog */}
      <Dialog open={jobDetailOpen} onOpenChange={(open) => {
        setJobDetailOpen(open);
        if (!open) {
          // Reset service photos when dialog closes
          setServicePhotos([]);
          setServiceNotes('');
        }
      }}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          {selectedJob && (
            <>
              <DialogHeader>
                <DialogTitle className="flex items-center gap-3">
                  <span className="job-license-plate text-2xl">{selectedJob.license_plate}</span>
                  {getStatusBadge(selectedJob.status, selectedJob.is_empty_trip)}
                </DialogTitle>
                <DialogDescription>
                  {selectedJob.job_number} • {selectedJob.tow_reason}
                </DialogDescription>
              </DialogHeader>

              {/* Edit & Delete Buttons - only show if job is not released */}
              {selectedJob.status !== 'released' && (
                <div className="flex justify-between items-center -mt-2">
                  {/* Delete button - only for early stages */}
                  {['pending', 'assigned', 'on_site'].includes(selectedJob.status) && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={handleDeleteJob}
                      disabled={deletingJob}
                      className="text-red-600 border-red-200 hover:bg-red-50"
                    >
                      {deletingJob ? (
                        <>
                          <div className="loading-spinner mr-2"></div>
                          Löscht...
                        </>
                      ) : (
                        <>
                          <X className="h-4 w-4 mr-2" />
                          Auftrag löschen
                        </>
                      )}
                    </Button>
                  )}
                  {!['pending', 'assigned', 'on_site'].includes(selectedJob.status) && <div />}

                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => openEditJobDialog(selectedJob)}
                    className="text-blue-600 border-blue-200 hover:bg-blue-50"
                  >
                    <Edit className="h-4 w-4 mr-2" />
                    Daten bearbeiten
                  </Button>
                </div>
              )}

              <div className="space-y-6 py-4">
                {/* Sicherstellung Details - prominent display */}
                {selectedJob.job_type === 'sicherstellung' && (
                  <div className="p-4 bg-amber-50 border border-amber-200 rounded-lg">
                    <h4 className="font-semibold text-amber-800 mb-3">⚠️ Sicherstellung (Polizeilich)</h4>
                    <div className="grid sm:grid-cols-2 gap-3 text-sm">
                      <div>
                        <Label className="text-amber-700">Grund</Label>
                        <p className="font-medium">{
                          {
                            'betriebsmittel': 'Auslaufende Betriebsmittel',
                            'gestohlen': 'Gestohlenes Fahrzeug / Fahndung',
                            'eigentumssicherung': 'Eigentumssicherung (wertvoll/ungesichert)',
                            'technische_maengel': 'Technische Mängel / Beweissicherung',
                            'strafrechtlich': 'Strafrechtliche Beschlagnahme'
                          }[selectedJob.sicherstellung_reason] || selectedJob.sicherstellung_reason || '-'
                        }</p>
                      </div>
                      <div>
                        <Label className="text-amber-700">Fahrzeugkategorie</Label>
                        <p className="font-medium">{
                          selectedJob.vehicle_category === 'under_3_5t' ? 'PKW/Krad bis 3,5t' :
                            selectedJob.vehicle_category === 'over_3_5t' ? 'Fahrzeuge ab 3,5t' : '-'
                        }</p>
                      </div>
                      {selectedJob.ordering_authority && (
                        <div>
                          <Label className="text-amber-700">Anordnende Stelle</Label>
                          <p className="font-medium">{
                            {
                              'schutzpolizei': 'Schutzpolizei',
                              'kriminalpolizei': 'Kriminalpolizei',
                              'staatsanwaltschaft': 'Staatsanwaltschaft',
                              'sachverstaendiger': 'Technischer Sachverständiger'
                            }[selectedJob.ordering_authority] || selectedJob.ordering_authority
                          }</p>
                        </div>
                      )}
                      {selectedJob.contact_attempts !== null && (
                        <div>
                          <Label className="text-amber-700">Telefonische Kontaktversuche</Label>
                          <p className="font-medium">{selectedJob.contact_attempts ? 'Ja' : 'Nein'}</p>
                          {selectedJob.contact_attempts_notes && (
                            <p className="text-xs text-amber-600 mt-1">{selectedJob.contact_attempts_notes}</p>
                          )}
                        </div>
                      )}
                      {selectedJob.estimated_vehicle_value && (
                        <div>
                          <Label className="text-amber-700">Geschätzter Wert</Label>
                          <p className="font-medium">{selectedJob.estimated_vehicle_value.toLocaleString('de-DE')} €</p>
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* Location Map */}
                <div className="map-container h-48">
                  <MapContainer
                    center={[selectedJob.location_lat, selectedJob.location_lng]}
                    zoom={15}
                    scrollWheelZoom={false}
                  >
                    <TileLayer
                      attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                      url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                    />
                    <Marker position={[selectedJob.location_lat, selectedJob.location_lng]}>
                      <Popup>
                        {(() => {
                          let addr = selectedJob.location_address || '';
                          // If it starts with coordinates like "52.379462, 9.724245 - Real Address"
                          if (/^\s*[-+]?\d{1,2}\.\d+,\s*[-+]?\d{1,3}\.\d+\s*[-|:]\s*/.test(addr)) {
                            addr = addr.replace(/^\s*[-+]?\d{1,2}\.\d+,\s*[-+]?\d{1,3}\.\d+\s*[-|:]\s*/, '').trim();
                          }
                          // If it's ONLY coordinates like "52.379462, 9.724245"
                          else if (/^\s*[-+]?\d{1,2}\.\d+,\s*[-+]?\d{1,3}\.\d+\s*$/.test(addr)) {
                            addr = "Keine genaue Adresse verfügbar";
                          }
                          return addr;
                        })()}
                      </Popup>
                    </Marker>
                  </MapContainer>
                </div>

                {/* Vehicle Details */}
                <div className="grid sm:grid-cols-2 gap-4">
                  <div>
                    <Label className="text-slate-500">Kennzeichen</Label>
                    <p className="font-bold">{selectedJob.license_plate}</p>
                  </div>
                  {selectedJob.vin && (
                    <div>
                      <Label className="text-slate-500">FIN</Label>
                      <p className="font-mono">{selectedJob.vin}</p>
                    </div>
                  )}
                  <div>
                    <Label className="text-slate-500">Erfasst von</Label>
                    <p>{selectedJob.created_by_name}</p>
                    <p className="text-sm text-slate-500">{selectedJob.created_by_authority}</p>
                  </div>
                </div>

                {/* NEW: Authority Yard Info (when target_yard = authority_yard) */}
                {selectedJob.target_yard === 'authority_yard' && (
                  <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
                    <Label className="text-green-800 font-semibold mb-2 block flex items-center gap-2">
                      <Building2 className="h-4 w-4" />
                      Ziel: Behörden-Hof
                    </Label>
                    <div className="space-y-1 text-sm">
                      {selectedJob.authority_yard_name && (
                        <p><strong>Hof:</strong> {selectedJob.authority_yard_name}</p>
                      )}
                      {selectedJob.authority_yard_address && (
                        <p><strong>Adresse:</strong> {selectedJob.authority_yard_address}</p>
                      )}
                      {selectedJob.authority_yard_phone && (
                        <p><strong>Telefon:</strong> {selectedJob.authority_yard_phone}</p>
                      )}
                      {selectedJob.authority_price_category_name && (
                        <p className="text-green-700 mt-2">
                          <strong>Preiskategorie:</strong> {selectedJob.authority_price_category_name}
                        </p>
                      )}
                    </div>
                    {selectedJob.authority_yard_address && (
                      <Button
                        variant="outline"
                        size="sm"
                        className="mt-3 text-green-700 border-green-300"
                        onClick={() => window.open(`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(selectedJob.authority_yard_address)}`, '_blank')}
                      >
                        <MapPin className="h-4 w-4 mr-2" />
                        Route zum Behörden-Hof
                      </Button>
                    )}
                  </div>
                )}

                {/* Timeline / Zeiterfassung */}
                <div className="bg-slate-50 rounded-lg p-4">
                  <Label className="text-slate-700 font-semibold mb-3 block flex items-center gap-2">
                    <Clock className="h-4 w-4" />
                    Zeiterfassung
                  </Label>
                  <div className="space-y-3">
                    <div className="flex items-center gap-3">
                      <div className={`w-3 h-3 rounded-full ${selectedJob.created_at ? 'bg-green-500' : 'bg-slate-300'}`}></div>
                      <div className="flex-1">
                        <p className="text-sm font-medium">1. Meldung erfasst</p>
                        <p className="text-sm text-slate-500">
                          {selectedJob.created_at ? new Date(selectedJob.created_at).toLocaleString('de-DE') : '-'}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <div className={`w-3 h-3 rounded-full ${selectedJob.on_site_at ? 'bg-green-500' : 'bg-slate-300'}`}></div>
                      <div className="flex-1">
                        <p className="text-sm font-medium">2. Vor Ort angekommen</p>
                        <p className="text-sm text-slate-500">
                          {selectedJob.on_site_at ? new Date(selectedJob.on_site_at).toLocaleString('de-DE') : '-'}
                        </p>
                      </div>
                    </div>
                    {selectedJob.is_empty_trip ? (
                      <div className="flex items-center gap-3">
                        <div className={`w-3 h-3 rounded-full ${selectedJob.status === 'empty_trip' || selectedJob.status === 'released' ? 'bg-orange-500' : 'bg-slate-300'}`}></div>
                        <div className="flex-1">
                          <p className="text-sm font-medium">3. Leerfahrt verzeichnet</p>
                          <p className="text-sm text-slate-500">
                            {selectedJob.updated_at ? new Date(selectedJob.updated_at).toLocaleString('de-DE') : '-'}
                          </p>
                        </div>
                      </div>
                    ) : (
                      <>
                        <div className="flex items-center gap-3">
                          <div className={`w-3 h-3 rounded-full ${selectedJob.towed_at ? 'bg-green-500' : 'bg-slate-300'}`}></div>
                          <div className="flex-1">
                            <p className="text-sm font-medium">3. Abgeschleppt</p>
                            <p className="text-sm text-slate-500">
                              {selectedJob.towed_at ? new Date(selectedJob.towed_at).toLocaleString('de-DE') : '-'}
                            </p>
                          </div>
                        </div>
                        <div className="flex items-center gap-3">
                          <div className={`w-3 h-3 rounded-full ${(selectedJob.in_yard_at || selectedJob.delivered_to_authority_at) ? 'bg-green-500' : 'bg-slate-300'}`}></div>
                          <div className="flex-1">
                            <p className="text-sm font-medium">
                              {selectedJob.target_yard === 'authority_yard' ? '4. An Behörde übergeben' : '4. Im Hof eingetroffen'}
                            </p>
                            <p className="text-sm text-slate-500">
                              {selectedJob.delivered_to_authority_at 
                                ? new Date(selectedJob.delivered_to_authority_at).toLocaleString('de-DE')
                                : selectedJob.in_yard_at 
                                  ? new Date(selectedJob.in_yard_at).toLocaleString('de-DE') 
                                  : '-'}
                            </p>
                          </div>
                        </div>
                        <div className="flex items-center gap-3">
                          <div className={`w-3 h-3 rounded-full ${selectedJob.released_at ? 'bg-green-500' : 'bg-slate-300'}`}></div>
                          <div className="flex-1">
                            <p className="text-sm font-medium">5. Fahrzeug abgeholt</p>
                            <p className="text-sm text-slate-500">
                              {selectedJob.released_at ? new Date(selectedJob.released_at).toLocaleString('de-DE') : '-'}
                            </p>
                          </div>
                        </div>
                      </>
                    )}
                  </div>
                </div>

                {/* Photos from Authority */}
                {selectedJob.photos && selectedJob.photos.length > 0 && (
                  <div>
                    <Label className="text-slate-500 mb-2 block">Fotos der Behörde ({selectedJob.photos.length})</Label>
                    <div className="grid grid-cols-4 gap-2">
                      {selectedJob.photos.map((photo, idx) => (
                        <div
                          key={idx}
                          className="relative aspect-square cursor-pointer hover:opacity-80 transition-opacity rounded-lg overflow-hidden border-2 border-slate-200 hover:border-orange-500"
                          onClick={() => openLightbox(selectedJob.photos, idx)}
                        >
                          <img
                            src={photo}
                            alt={`Foto ${idx + 1}`}
                            className="w-full h-full object-cover"
                          />
                          <div className="absolute inset-0 flex items-center justify-center bg-black/0 hover:bg-black/30 transition-colors">
                            <Search className="h-6 w-6 text-white opacity-0 hover:opacity-100" />
                          </div>
                        </div>
                      ))}
                    </div>
                    <p className="text-xs text-slate-400 mt-1">Klicken zum Vergrößern</p>
                  </div>
                )}

                {/* Notes */}
                <div>
                  <Label htmlFor="serviceNotes" className="text-slate-500">Eigene Bemerkungen</Label>
                  <Textarea
                    id="serviceNotes"
                    value={serviceNotes}
                    onChange={(e) => setServiceNotes(e.target.value)}
                    placeholder="Beschreibung oder Anmerkungen hinzufügen..."
                    rows={2}
                    className="mt-1"
                  />
                </div>

                {/* Add Photo */}
                <div>
                  <Label className="text-slate-500 mb-2 block">Foto hinzufügen</Label>
                  <div className="flex gap-2">
                    {servicePhotos.map((photo, idx) => (
                      <div key={idx} className="relative w-16 h-16">
                        <img src={photo} alt="" className="w-full h-full object-cover rounded" />
                        <button
                          onClick={() => setServicePhotos(prev => prev.filter((_, i) => i !== idx))}
                          className="absolute -top-1 -right-1 bg-red-500 text-white rounded-full p-0.5"
                        >
                          <X className="h-3 w-3" />
                        </button>
                      </div>
                    ))}
                    <button
                      onClick={() => fileInputRef.current?.click()}
                      className="w-16 h-16 border-2 border-dashed border-slate-300 rounded flex items-center justify-center hover:border-slate-400"
                    >
                      <Camera className="h-5 w-5 text-slate-400" />
                    </button>
                  </div>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="image/*"
                    capture="environment"
                    onChange={handlePhotoUpload}
                    className="hidden"
                  />
                </div>

                {/* Status Actions */}
                <div className="border-t pt-4">
                  <Label className="text-slate-500 mb-3 block">Status aktualisieren</Label>
                  <div className="flex flex-wrap gap-2">
                    {selectedJob.status === 'assigned' && (
                      <Button
                        data-testid="status-on-site-btn"
                        onClick={() => handleStatusUpdate(selectedJob.id, 'on_site')}
                        className="bg-orange-500 hover:bg-orange-600"
                      >
                        <MapPin className="h-4 w-4 mr-2" />
                        Bin vor Ort
                      </Button>
                    )}
                    {selectedJob.status === 'on_site' && (
                      <div className="flex gap-2">
                        <Button
                          data-testid="status-stepback-btn"
                          variant="outline"
                          onClick={() => handleStatusUpdate(selectedJob.id, 'assigned')}
                          className="text-slate-600 hover:text-slate-800"
                        >
                          <Undo2 className="h-4 w-4 mr-2" />
                          Zurück
                        </Button>
                        <Button
                          data-testid="status-towed-btn"
                          onClick={() => handleStatusUpdate(selectedJob.id, 'towed')}
                          className="bg-red-500 hover:bg-red-600"
                        >
                          <Truck className="h-4 w-4 mr-2" />
                          Abgeschleppt
                        </Button>
                        <Button
                          data-testid="status-empty-trip-btn"
                          onClick={openEmptyTripDialog}
                          variant="outline"
                          className="border-orange-500 text-orange-600 hover:bg-orange-50"
                        >
                          <X className="h-4 w-4 mr-2" />
                          Leerfahrt
                        </Button>
                      </div>
                    )}
                    {selectedJob.status === 'towed' && (
                      <div className="flex gap-2">
                        <Button
                          data-testid="status-stepback-btn"
                          variant="outline"
                          onClick={() => handleStatusUpdate(selectedJob.id, 'on_site')}
                          className="text-slate-600 hover:text-slate-800"
                        >
                          <Undo2 className="h-4 w-4 mr-2" />
                          Zurück
                        </Button>
                        <Button
                          data-testid="status-in-yard-btn"
                          onClick={() => handleStatusUpdate(selectedJob.id, 'in_yard')}
                          className={selectedJob.target_yard === 'authority_yard' ? "bg-purple-500 hover:bg-purple-600" : "bg-yellow-500 hover:bg-yellow-600"}
                        >
                          <Building2 className="h-4 w-4 mr-2" />
                          {selectedJob.target_yard === 'authority_yard' ? 'An Behörde übergeben' : 'Im Hof angekommen'}
                        </Button>
                      </div>
                    )}
                    {/* Standard: Fahrzeug im eigenen Hof */}
                    {selectedJob.status === 'in_yard' && selectedJob.target_yard !== 'authority_yard' && (
                      <div className="flex gap-2">
                        <Button
                          data-testid="status-stepback-btn"
                          variant="outline"
                          onClick={() => handleStatusUpdate(selectedJob.id, 'towed')}
                          className="text-slate-600 hover:text-slate-800"
                        >
                          <Undo2 className="h-4 w-4 mr-2" />
                          Zurück
                        </Button>
                        <Button
                          data-testid="status-release-btn"
                          onClick={() => {
                            setReleaseDialogOpen(true);
                            fetchCalculatedCosts(selectedJob.id);
                          }}
                          className="bg-green-500 hover:bg-green-600"
                        >
                          <CheckCircle className="h-4 w-4 mr-2" />
                          Fahrzeug freigeben
                        </Button>
                      </div>
                    )}
                    {/* Behörden-Hof: Fahrzeug wurde übergeben - Auftrag abgeschlossen */}
                    {(selectedJob.status === 'delivered_to_authority' || (selectedJob.status === 'in_yard' && selectedJob.target_yard === 'authority_yard')) && (
                      <div className="p-4 bg-purple-50 border border-purple-200 rounded-lg">
                        <div className="flex items-center gap-2 text-purple-800">
                          <CheckCircle className="h-5 w-5" />
                          <span className="font-semibold">Fahrzeug an Behörde übergeben</span>
                        </div>
                        <p className="text-sm text-purple-600 mt-1">
                          Ihr Auftrag ist abgeschlossen. Die Behörde übernimmt die Freigabe.
                          Sie erhalten eine Rechnung nach der Fahrzeugfreigabe.
                        </p>
                      </div>
                    )}
                  </div>
                </div>

                <a
                  href={`https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent(selectedJob.location_address || `${selectedJob.location_lat},${selectedJob.location_lng}`)}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-2 text-orange-600 hover:text-orange-700"
                >
                  <MapPin className="h-4 w-4" />
                  Navigation starten
                </a>
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>

      {/* Release Dialog */}
      <Dialog open={releaseDialogOpen} onOpenChange={setReleaseDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Fahrzeug freigeben</DialogTitle>
            <DialogDescription>
              Geben Sie die Daten des Halters und die Zahlungsinformationen ein
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="ownerFirstName">Vorname *</Label>
                <Input
                  data-testid="release-firstname-input"
                  id="ownerFirstName"
                  value={ownerFirstName}
                  onChange={(e) => setOwnerFirstName(e.target.value)}
                  placeholder="Max"
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="ownerLastName">Nachname *</Label>
                <Input
                  data-testid="release-lastname-input"
                  id="ownerLastName"
                  value={ownerLastName}
                  onChange={(e) => setOwnerLastName(e.target.value)}
                  placeholder="Mustermann"
                  required
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="ownerAddress">Adresse</Label>
              <Input
                data-testid="release-address-input"
                id="ownerAddress"
                value={ownerAddress}
                onChange={(e) => setOwnerAddress(e.target.value)}
                placeholder="Musterstraße 1, 12345 Berlin"
              />
            </div>

            <div className="space-y-2">
              <Label>Zahlungsart *</Label>
              <RadioGroup value={paymentMethod} onValueChange={setPaymentMethod}>
                <div className="flex items-center space-x-4">
                  <div className="flex items-center space-x-2">
                    <RadioGroupItem value="cash" id="cash" />
                    <Label htmlFor="cash">Bar</Label>
                  </div>
                  <div className="flex items-center space-x-2">
                    <RadioGroupItem value="card" id="card" />
                    <Label htmlFor="card">Karte</Label>
                  </div>
                </div>
              </RadioGroup>
            </div>

            {/* Price Calculation Section */}
            <div className="space-y-3 p-4 bg-slate-50 rounded-lg border">
              <Label className="font-semibold">Kostenberechnung</Label>

              {/* Calculated Costs from Backend */}
              {loadingCosts ? (
                <div className="flex justify-center py-4">
                  <div className="loading-spinner"></div>
                </div>
              ) : calculatedCosts && calculatedCosts.breakdown?.length > 0 ? (
                <div className="text-sm text-slate-600 space-y-1">
                  {calculatedCosts.breakdown.map((item, idx) => (
                    <div key={idx} className="flex justify-between">
                      <span>{item.label}:</span>
                      <span>{item.amount.toFixed(2)} €</span>
                    </div>
                  ))}
                  <div className="flex justify-between font-bold border-t pt-2 mt-2">
                    <span>Berechneter Gesamtpreis:</span>
                    <span className="text-green-600">{calculatedCosts.total.toFixed(2)} €</span>
                  </div>
                </div>
              ) : selectedJob?.in_yard_at ? (
                <div className="text-sm text-slate-600 space-y-1">
                  <div className="flex justify-between">
                    <span>Anfahrtskosten:</span>
                    <span>{(user?.tow_cost || 0).toFixed(2)} €</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Standtage:</span>
                    <span>{Math.max(1, Math.ceil((new Date() - new Date(selectedJob.in_yard_at)) / (1000 * 60 * 60 * 24)))} Tag(e)</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Standkosten ({(user?.daily_cost || 0).toFixed(2)} €/Tag):</span>
                    <span>{(Math.max(1, Math.ceil((new Date() - new Date(selectedJob.in_yard_at)) / (1000 * 60 * 60 * 24))) * (user?.daily_cost || 0)).toFixed(2)} €</span>
                  </div>
                  <div className="flex justify-between font-bold border-t pt-2 mt-2">
                    <span>Berechneter Gesamtpreis:</span>
                    <span className="text-green-600">
                      {((user?.tow_cost || 0) + Math.max(1, Math.ceil((new Date() - new Date(selectedJob.in_yard_at)) / (1000 * 60 * 60 * 24))) * (user?.daily_cost || 0)).toFixed(2)} €
                    </span>
                  </div>
                </div>
              ) : null}

              <div className="flex gap-2 mt-3">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    if (selectedJob?.in_yard_at) {
                      const days = Math.max(1, Math.ceil((new Date() - new Date(selectedJob.in_yard_at)) / (1000 * 60 * 60 * 24)));
                      const total = (user?.tow_cost || 0) + days * (user?.daily_cost || 0);
                      setPaymentAmount(total.toFixed(2));
                    }
                  }}
                  className="flex-1"
                >
                  <Euro className="h-4 w-4 mr-1" />
                  Berechnung übernehmen
                </Button>
              </div>

              <div className="space-y-2 mt-3">
                <Label htmlFor="paymentAmount" className="text-sm text-slate-500">Oder manuell eingeben:</Label>
                <Input
                  data-testid="release-amount-input"
                  id="paymentAmount"
                  type="number"
                  step="0.01"
                  value={paymentAmount}
                  onChange={(e) => setPaymentAmount(e.target.value)}
                  placeholder="Betrag eingeben..."
                  className="text-lg font-bold"
                  required
                />
              </div>
            </div>

            <Button
              data-testid="confirm-release-btn"
              onClick={handleReleaseVehicle}
              className="w-full bg-green-600 hover:bg-green-700"
            >
              <CheckCircle className="h-4 w-4 mr-2" />
              Freigabe bestätigen & PDF erstellen
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* NEW: Empty Trip (Leerfahrt) Dialog */}
      <Dialog open={emptyTripDialogOpen} onOpenChange={setEmptyTripDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <X className="h-5 w-5 text-orange-600" />
              Leerfahrt erfassen
            </DialogTitle>
            <DialogDescription>
              {selectedJob?.license_plate} - {selectedJob?.job_number}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-6 py-4">
            {/* Reason Selection */}
            <div className="space-y-3">
              <Label className="font-medium">Grund der Leerfahrt *</Label>
              <div className="space-y-2">
                <label className={`flex items-center gap-3 p-3 border rounded-lg cursor-pointer transition-colors ${emptyTripReason === 'vehicle_gone' ? 'border-orange-500 bg-orange-50' : 'border-slate-200 hover:bg-slate-50'}`}>
                  <input
                    type="radio"
                    name="emptyTripReason"
                    value="vehicle_gone"
                    checked={emptyTripReason === 'vehicle_gone'}
                    onChange={(e) => setEmptyTripReason(e.target.value)}
                    className="w-4 h-4"
                  />
                  <div>
                    <span className="font-medium">Fahrzeug nicht mehr vor Ort</span>
                    <span className="text-xs text-slate-500 block">Auto war bei Ankunft bereits weg</span>
                  </div>
                </label>
                <label className={`flex items-center gap-3 p-3 border rounded-lg cursor-pointer transition-colors ${emptyTripReason === 'driver_present' ? 'border-orange-500 bg-orange-50' : 'border-slate-200 hover:bg-slate-50'}`}>
                  <input
                    type="radio"
                    name="emptyTripReason"
                    value="driver_present"
                    checked={emptyTripReason === 'driver_present'}
                    onChange={(e) => setEmptyTripReason(e.target.value)}
                    className="w-4 h-4"
                  />
                  <div>
                    <span className="font-medium">Halter vor Ort angetroffen</span>
                    <span className="text-xs text-slate-500 block">Halter konnte Fahrzeug selbst entfernen</span>
                  </div>
                </label>
                <label className={`flex items-center gap-3 p-3 border rounded-lg cursor-pointer transition-colors ${emptyTripReason === 'driver_not_found' ? 'border-red-500 bg-red-50' : 'border-slate-200 hover:bg-slate-50'}`}>
                  <input
                    type="radio"
                    name="emptyTripReason"
                    value="driver_not_found"
                    checked={emptyTripReason === 'driver_not_found'}
                    onChange={(e) => {
                      setEmptyTripReason(e.target.value);
                      setEmptyTripPaymentAmount('0');
                    }}
                    className="w-4 h-4"
                  />
                  <div>
                    <span className="font-medium text-red-700">Halter nicht aufgetaucht</span>
                    <span className="text-xs text-red-500 block">Fahrzeug nicht gefunden - Kosten offen</span>
                  </div>
                </label>
              </div>
            </div>

            {/* Warning for driver_not_found */}
            {emptyTripReason === 'driver_not_found' && (
              <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
                <p className="text-sm text-red-800">
                  <strong>⚠️ Kosten offen!</strong><br />
                  Die Behörde wird benachrichtigt und muss den Halter mit Kennzeichen <strong>{selectedJob?.license_plate}</strong> kontaktieren, um die Leerfahrt-Kosten einzufordern.
                </p>
              </div>
            )}

            {/* Driver Info - only if driver present */}
            {emptyTripReason === 'driver_present' && (
              <div className="space-y-4 p-4 bg-slate-50 border rounded-lg">
                <h4 className="font-medium text-slate-700">Fahrer-/Halterdaten</h4>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="emptyTripFirstName">Vorname *</Label>
                    <Input
                      id="emptyTripFirstName"
                      value={emptyTripDriverFirstName}
                      onChange={(e) => setEmptyTripDriverFirstName(e.target.value)}
                      placeholder="Max"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="emptyTripLastName">Nachname *</Label>
                    <Input
                      id="emptyTripLastName"
                      value={emptyTripDriverLastName}
                      onChange={(e) => setEmptyTripDriverLastName(e.target.value)}
                      placeholder="Mustermann"
                    />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="emptyTripAddress">Adresse</Label>
                  <Input
                    id="emptyTripAddress"
                    value={emptyTripDriverAddress}
                    onChange={(e) => setEmptyTripDriverAddress(e.target.value)}
                    placeholder="Musterstraße 1, 12345 Berlin"
                  />
                </div>
              </div>
            )}

            {/* Payment Section - only show if not driver_not_found OR if they want to charge */}
            <div className={`space-y-4 p-4 ${emptyTripReason === 'driver_not_found' ? 'bg-red-50 border border-red-200' : 'bg-orange-50 border border-orange-200'} rounded-lg`}>
              <h4 className={`font-medium ${emptyTripReason === 'driver_not_found' ? 'text-red-800' : 'text-orange-800'}`}>
                {emptyTripReason === 'driver_not_found' ? 'Leerfahrt-Kosten (offen)' : 'Leerfahrt-Kosten'}
              </h4>

              {/* Show configured empty trip fee */}
              {user?.empty_trip_fee > 0 && emptyTripReason !== 'driver_not_found' && (
                <div className="flex justify-between items-center text-sm">
                  <span className="text-orange-700">Ihr Leerfahrt-Preis:</span>
                  <span className="font-bold text-orange-900">{user.empty_trip_fee.toFixed(2)} €</span>
                </div>
              )}

              {emptyTripReason !== 'driver_not_found' && (
                <div className="space-y-2">
                  <Label>Zahlungsart *</Label>
                  <RadioGroup value={emptyTripPaymentMethod} onValueChange={setEmptyTripPaymentMethod}>
                    <div className="flex items-center space-x-4">
                      <div className="flex items-center space-x-2">
                        <RadioGroupItem value="cash" id="emptyTripCash" />
                        <Label htmlFor="emptyTripCash" className="cursor-pointer">Bar</Label>
                      </div>
                      <div className="flex items-center space-x-2">
                        <RadioGroupItem value="card" id="emptyTripCard" />
                        <Label htmlFor="emptyTripCard" className="cursor-pointer">Karte</Label>
                      </div>
                      <div className="flex items-center space-x-2">
                        <RadioGroupItem value="invoice" id="emptyTripInvoice" />
                        <Label htmlFor="emptyTripInvoice" className="cursor-pointer">Rechnung</Label>
                      </div>
                    </div>
                  </RadioGroup>
                </div>
              )}

              <div className="space-y-2">
                <div className="flex justify-between items-center">
                  <Label htmlFor="emptyTripAmount">
                    {emptyTripReason === 'driver_not_found' ? 'Offener Betrag (€)' : 'Betrag (€) *'}
                  </Label>
                  {user?.empty_trip_fee > 0 && emptyTripPaymentAmount !== user.empty_trip_fee.toString() && emptyTripReason !== 'driver_not_found' && (
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => setEmptyTripPaymentAmount(user.empty_trip_fee.toString())}
                      className="text-xs text-orange-600"
                    >
                      Standard übernehmen
                    </Button>
                  )}
                </div>
                <Input
                  id="emptyTripAmount"
                  type="number"
                  step="0.01"
                  value={emptyTripPaymentAmount}
                  onChange={(e) => setEmptyTripPaymentAmount(e.target.value)}
                  placeholder="Betrag eingeben..."
                  className="text-lg font-bold"
                />
              </div>
            </div>

            {/* Submit Buttons */}
            <div className="flex gap-3 pt-2">
              <Button
                variant="outline"
                onClick={() => setEmptyTripDialogOpen(false)}
                className="flex-1"
              >
                Abbrechen
              </Button>
              <Button
                onClick={handleEmptyTripSubmit}
                disabled={submittingEmptyTrip}
                className="flex-1 bg-orange-600 hover:bg-orange-700"
              >
                {submittingEmptyTrip ? (
                  <>
                    <div className="loading-spinner h-4 w-4 mr-2"></div>
                    Verarbeite...
                  </>
                ) : (
                  <>
                    <FileText className="h-4 w-4 mr-2" />
                    Leerfahrt & PDF
                  </>
                )}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* NEW: Company Info Dialog */}
      <Dialog open={companyInfoDialogOpen} onOpenChange={setCompanyInfoDialogOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Building2 className="h-5 w-5 text-blue-600" />
              Firmendaten bearbeiten
            </DialogTitle>
            <DialogDescription>
              Diese Daten werden bei der Fahrzeugsuche angezeigt
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="companyName">Firmenname</Label>
              <Input
                id="companyName"
                value={companyName}
                onChange={(e) => setCompanyName(e.target.value)}
                placeholder="Mustermann Abschleppdienst GmbH"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="companyPhone">Telefonnummer</Label>
                <Input
                  id="companyPhone"
                  value={companyPhone}
                  onChange={(e) => setCompanyPhone(e.target.value)}
                  placeholder="+49 123 456789"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="companyEmail">E-Mail</Label>
                <Input
                  id="companyEmail"
                  type="email"
                  value={companyEmail}
                  onChange={(e) => setCompanyEmail(e.target.value)}
                  placeholder="info@firma.de"
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="companyOpeningHours">Öffnungszeiten</Label>
              <Input
                id="companyOpeningHours"
                value={companyOpeningHours}
                onChange={(e) => setCompanyOpeningHours(e.target.value)}
                placeholder="Mo-Fr 8:00-18:00, Sa 9:00-14:00"
              />
            </div>

            <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg space-y-4">
              <h4 className="font-medium text-blue-800 flex items-center gap-2">
                <MapPin className="h-4 w-4" />
                Hof-Adresse (für Fahrzeugabholung)
              </h4>

              <div className="space-y-2">
                <Label htmlFor="companyYardAddress">Adresse</Label>
                <Input
                  id="companyYardAddress"
                  value={companyYardAddress}
                  onChange={(e) => setCompanyYardAddress(e.target.value)}
                  placeholder="Hofstraße 1, 12345 Berlin"
                />
              </div>

              <Button
                type="button"
                variant="outline"
                onClick={handleGetYardLocation}
                className="w-full"
              >
                <MapPin className="h-4 w-4 mr-2" />
                GPS-Koordinaten vom aktuellen Standort erfassen
              </Button>

              {companyYardLat && companyYardLng && (
                <div className="text-sm text-blue-700 bg-blue-100 p-2 rounded">
                  ✓ Koordinaten: {companyYardLat.toFixed(6)}, {companyYardLng.toFixed(6)}
                </div>
              )}
            </div>

            <div className="flex gap-3 pt-4 border-t">
              <Button
                variant="outline"
                onClick={() => setCompanyInfoDialogOpen(false)}
                className="flex-1"
              >
                Abbrechen
              </Button>
              <Button
                onClick={handleSaveCompanyInfo}
                disabled={savingCompanyInfo}
                className="flex-1 bg-blue-600 hover:bg-blue-700"
              >
                {savingCompanyInfo ? 'Speichert...' : 'Speichern'}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* NEW: Create Job Dialog - Same layout as Authority Dashboard */}
      <Dialog open={createJobDialogOpen} onOpenChange={setCreateJobDialogOpen}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-xl">
              <Plus className="h-6 w-6 text-green-600" />
              Neuer Auftrag
            </DialogTitle>
            <DialogDescription>
              Erstellen Sie einen Auftrag für eine verknüpfte Behörde
            </DialogDescription>
          </DialogHeader>

          {loadingAuthorities ? (
            <div className="flex items-center justify-center py-12">
              <div className="loading-spinner h-8 w-8"></div>
              <span className="ml-3 text-slate-500">Lade verknüpfte Behörden...</span>
            </div>
          ) : linkedAuthorities.length === 0 ? (
            <div className="p-6 bg-yellow-50 border border-yellow-200 rounded-lg text-yellow-800 text-center">
              <Building2 className="h-12 w-12 mx-auto mb-3 text-yellow-600" />
              <p className="font-semibold text-lg">Keine verknüpften Behörden</p>
              <p className="text-sm mt-2">
                Um Aufträge erstellen zu können, muss eine Behörde Sie zuerst über Ihren Verknüpfungscode hinzufügen.
              </p>
              <p className="text-sm mt-2 font-medium">
                Ihr Code: <span className="font-mono bg-yellow-100 px-2 py-1 rounded">{user?.service_code}</span>
              </p>
            </div>
          ) : (
            <div className="grid md:grid-cols-2 gap-6 py-4">
              {/* Left Column - Vehicle & Authority Info */}
              <div className="space-y-6">
                {/* Authority Selection Card */}
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2 text-base">
                      <Building2 className="h-5 w-5" />
                      Behörde auswählen
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <Select
                      value={newJobData.for_authority_id}
                      onValueChange={(value) => setNewJobData(prev => ({ ...prev, for_authority_id: value }))}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Behörde auswählen..." />
                      </SelectTrigger>
                      <SelectContent>
                        {linkedAuthorities.map(auth => (
                          <SelectItem key={auth.id} value={auth.id}>
                            {auth.authority_name} {auth.department ? `(${auth.department})` : ''}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </CardContent>
                </Card>

                {/* Vehicle Info Card */}
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2 text-base">
                      <Car className="h-5 w-5" />
                      Fahrzeugdaten
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    {/* Job Type Selection */}
                    <div className="space-y-3">
                      <Label>Art des Auftrags *</Label>
                      <div className="flex gap-4">
                        <label className={`flex items-center gap-2 p-3 border rounded-lg cursor-pointer transition-colors flex-1 ${newJobData.job_type === 'towing' ? 'border-blue-500 bg-blue-50' : 'border-slate-200 hover:bg-slate-50'}`}>
                          <input
                            type="radio"
                            name="newJobType"
                            value="towing"
                            checked={newJobData.job_type === 'towing'}
                            onChange={(e) => setNewJobData(prev => ({ ...prev, job_type: e.target.value }))}
                            className="w-4 h-4"
                          />
                          <div>
                            <span className="font-medium">Abschleppen</span>
                            <span className="text-xs text-slate-500 block">Falschparker</span>
                          </div>
                        </label>
                        <label className={`flex items-center gap-2 p-3 border rounded-lg cursor-pointer transition-colors flex-1 ${newJobData.job_type === 'sicherstellung' ? 'border-amber-500 bg-amber-50' : 'border-slate-200 hover:bg-slate-50'}`}>
                          <input
                            type="radio"
                            name="newJobType"
                            value="sicherstellung"
                            checked={newJobData.job_type === 'sicherstellung'}
                            onChange={(e) => setNewJobData(prev => ({ ...prev, job_type: e.target.value }))}
                            className="w-4 h-4"
                          />
                          <div>
                            <span className="font-medium">Sicherstellung</span>
                            <span className="text-xs text-slate-500 block">Polizeilich</span>
                          </div>
                        </label>
                      </div>
                    </div>

                    {/* Sicherstellung-specific fields */}
                    {newJobData.job_type === 'sicherstellung' && (
                      <div className="space-y-4 p-4 bg-amber-50 border border-amber-200 rounded-lg">
                        <h4 className="font-semibold text-amber-800">Sicherstellungs-Details</h4>

                        <div className="grid grid-cols-2 gap-4">
                          <div className="space-y-2">
                            <Label>Grund der Sicherstellung *</Label>
                            <Select value={newJobData.sicherstellung_reason} onValueChange={(val) => setNewJobData(prev => ({ ...prev, sicherstellung_reason: val }))}>
                              <SelectTrigger>
                                <SelectValue placeholder="Grund auswählen" />
                              </SelectTrigger>
                              <SelectContent>
                                <SelectItem value="betriebsmittel">Auslaufende Betriebsmittel</SelectItem>
                                <SelectItem value="gestohlen">Gestohlenes Fahrzeug / Fahndung</SelectItem>
                                <SelectItem value="eigentumssicherung">Eigentumssicherung</SelectItem>
                                <SelectItem value="technische_maengel">Technische Mängel</SelectItem>
                                <SelectItem value="strafrechtlich">Strafrechtliche Beschlagnahme</SelectItem>
                              </SelectContent>
                            </Select>
                          </div>

                          <div className="space-y-2">
                            <Label>Fahrzeugkategorie</Label>
                            <Select value={newJobData.vehicle_category} onValueChange={(val) => setNewJobData(prev => ({ ...prev, vehicle_category: val }))}>
                              <SelectTrigger>
                                <SelectValue />
                              </SelectTrigger>
                              <SelectContent>
                                <SelectItem value="under_3_5t">PKW/Krad bis 3,5t</SelectItem>
                                <SelectItem value="over_3_5t">Fahrzeuge ab 3,5t</SelectItem>
                              </SelectContent>
                            </Select>
                          </div>

                          <div className="space-y-2">
                            <Label>Anordnende Stelle</Label>
                            <Select value={newJobData.ordering_authority} onValueChange={(val) => setNewJobData(prev => ({ ...prev, ordering_authority: val }))}>
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
                              value={newJobData.estimated_vehicle_value}
                              onChange={(e) => setNewJobData(prev => ({ ...prev, estimated_vehicle_value: e.target.value }))}
                              placeholder="z.B. 15000"
                            />
                          </div>
                        </div>

                        <div className="space-y-2">
                          <div className="flex items-center gap-2">
                            <input
                              type="checkbox"
                              id="newContactAttempts"
                              checked={newJobData.contact_attempts}
                              onChange={(e) => setNewJobData(prev => ({ ...prev, contact_attempts: e.target.checked }))}
                              className="w-4 h-4"
                            />
                            <Label htmlFor="newContactAttempts" className="cursor-pointer">
                              Telefonische Kontaktversuche durchgeführt
                            </Label>
                          </div>
                          {newJobData.contact_attempts && (
                            <Textarea
                              value={newJobData.contact_attempts_notes}
                              onChange={(e) => setNewJobData(prev => ({ ...prev, contact_attempts_notes: e.target.value }))}
                              placeholder="Dokumentation der Kontaktversuche..."
                              rows={2}
                              className="mt-2"
                            />
                          )}
                        </div>
                      </div>
                    )}

                    <div className="space-y-2">
                      <Label htmlFor="newLicensePlate">Kennzeichen (oder FIN) *</Label>
                      <Input
                        id="newLicensePlate"
                        value={newJobData.license_plate}
                        onChange={(e) => setNewJobData(prev => ({ ...prev, license_plate: e.target.value.toUpperCase() }))}
                        placeholder="B-AB 1234"
                        className="license-plate-input text-xl uppercase"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="newVin">Fahrzeug-Identifizierungsnummer (FIN)</Label>
                      <Input
                        id="newVin"
                        value={newJobData.vin}
                        onChange={(e) => setNewJobData(prev => ({ ...prev, vin: e.target.value.toUpperCase() }))}
                        placeholder="WVWZZZ3CZWE123456"
                        className="font-mono uppercase"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="newTowReason">Abschleppgrund *</Label>
                      <Select value={newJobData.tow_reason} onValueChange={(val) => setNewJobData(prev => ({ ...prev, tow_reason: val }))}>
                        <SelectTrigger>
                          <SelectValue placeholder="Grund auswählen" />
                        </SelectTrigger>
                        <SelectContent className="max-h-[300px]">
                          <SelectItem value="Parken im Parkverbot">Parken im Parkverbot</SelectItem>
                          <SelectItem value="Parken in Feuerwehrzufahrt">Parken in Feuerwehrzufahrt</SelectItem>
                          <SelectItem value="Parken auf Behindertenparkplatz">Parken auf Behindertenparkplatz</SelectItem>
                          <SelectItem value="Zugeparkte Ausfahrt">Zugeparkte Ausfahrt</SelectItem>
                          <SelectItem value="Gefährdendes Parken">Gefährdendes Parken</SelectItem>
                          <SelectItem value="Fahrzeug ohne gültige Zulassung im öffentlichen Raum">Fahrzeug ohne gültige Zulassung im öffentlichen Raum</SelectItem>
                          <SelectItem value="Fahrzeug ohne Kennzeichen">Fahrzeug ohne Kennzeichen</SelectItem>
                          <SelectItem value="Blockieren einer Feuerwehrzufahrt">Blockieren einer Feuerwehrzufahrt</SelectItem>
                          <SelectItem value="Blockieren von Rettungswegen">Blockieren von Rettungswegen</SelectItem>
                          <SelectItem value="Blockieren von Notausfahrten">Blockieren von Notausfahrten</SelectItem>
                          <SelectItem value="Parken im Sicherheitsbereich von Polizei- oder Feuerwehreinsätzen">Parken im Sicherheitsbereich von Polizei- oder Feuerwehreinsätzen</SelectItem>
                          <SelectItem value="Parken auf einem E-Auto-Ladeplatz ohne Ladevorgang">Parken auf einem E-Auto-Ladeplatz ohne Ladevorgang</SelectItem>
                          <SelectItem value="Parken auf einem Carsharing-Parkplatz ohne Berechtigung">Parken auf einem Carsharing-Parkplatz ohne Berechtigung</SelectItem>
                          <SelectItem value="Parken auf einem Bewohnerparkplatz ohne gültigen Ausweis">Parken auf einem Bewohnerparkplatz ohne gültigen Ausweis</SelectItem>
                          <SelectItem value="Öl Verlust">Öl Verlust</SelectItem>
                          <SelectItem value="Sonstiges">Sonstiges</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="newNotes">Bemerkungen</Label>
                      <Textarea
                        id="newNotes"
                        value={newJobData.notes}
                        onChange={(e) => setNewJobData(prev => ({ ...prev, notes: e.target.value }))}
                        placeholder="Zusätzliche Informationen..."
                        rows={3}
                      />
                    </div>
                  </CardContent>
                </Card>
              </div>

              {/* Right Column - Location & Photos */}
              <div className="space-y-6">
                {/* Location Card */}
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2 text-base">
                      <MapPin className="h-5 w-5" />
                      Standort
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <Button
                      type="button"
                      onClick={handleGetNewJobLocation}
                      variant="outline"
                      className="w-full"
                    >
                      <MapPin className="h-4 w-4 mr-2" />
                      Aktuellen Standort erfassen
                    </Button>
                    <div className="space-y-2">
                      <Label htmlFor="newLocationAddress">Adresse *</Label>
                      <Input
                        id="newLocationAddress"
                        value={newJobData.location_address}
                        onChange={(e) => setNewJobData(prev => ({ ...prev, location_address: e.target.value }))}
                        placeholder="Straße, Hausnummer, PLZ, Stadt"
                      />
                    </div>
                    <div className="map-container h-48 rounded-lg overflow-hidden border">
                      <MapContainer
                        center={newJobPosition || [52.520008, 13.404954]}
                        zoom={newJobPosition ? 16 : 10}
                        scrollWheelZoom={true}
                        style={{ height: '100%', width: '100%' }}
                      >
                        <TileLayer
                          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                        />
                        <LocationPicker position={newJobPosition} setPosition={handleNewJobMapClick} />
                      </MapContainer>
                    </div>
                    <p className="text-xs text-slate-500">
                      Klicken Sie auf die Karte, um den Standort manuell zu setzen
                    </p>
                  </CardContent>
                </Card>

                {/* Photos Card */}
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2 text-base">
                      <Camera className="h-5 w-5" />
                      Fotos ({newJobPhotos.length}/5)
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="photo-upload-grid">
                      {[...Array(5)].map((_, index) => (
                        <div
                          key={index}
                          className="photo-upload-slot"
                          onClick={() => index >= newJobPhotos.length && newJobFileInputRef.current?.click()}
                        >
                          {newJobPhotos[index] ? (
                            <div className="relative w-full h-full group">
                              <img src={newJobPhotos[index]} alt={`Foto ${index + 1}`} className="w-full h-full object-cover" />
                              <button
                                type="button"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  removeNewJobPhoto(index);
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
                      ref={newJobFileInputRef}
                      type="file"
                      accept="image/*"
                      capture="environment"
                      multiple
                      onChange={handleNewJobPhotoUpload}
                      className="hidden"
                    />
                  </CardContent>
                </Card>

                {/* Submit Button */}
                <div className="flex gap-3">
                  <Button
                    variant="outline"
                    onClick={() => setCreateJobDialogOpen(false)}
                    className="flex-1"
                  >
                    Abbrechen
                  </Button>
                  <Button
                    onClick={handleCreateJob}
                    disabled={creatingJob || !newJobData.for_authority_id}
                    className="flex-1 bg-green-600 hover:bg-green-700"
                  >
                    {creatingJob ? (
                      <>
                        <div className="loading-spinner h-4 w-4 mr-2"></div>
                        Erstelle...
                      </>
                    ) : (
                      <>
                        <CheckCircle className="h-4 w-4 mr-2" />
                        Auftrag erstellen
                      </>
                    )}
                  </Button>
                </div>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Photo Lightbox Dialog */}
      <Dialog open={lightboxOpen} onOpenChange={setLightboxOpen}>
        <DialogContent className="max-w-4xl p-0 bg-black/95 border-none">
          {/* Accessibility: Visually hidden title for screen readers */}
          <VisuallyHidden>
            <DialogTitle>Fotoansicht</DialogTitle>
          </VisuallyHidden>
          <VisuallyHidden>
            <DialogDescription>Vollbildansicht des ausgewählten Fotos. Verwenden Sie die Pfeiltasten zur Navigation zwischen Fotos.</DialogDescription>
          </VisuallyHidden>
          <div className="relative">
            {/* Close Button */}
            <button
              onClick={() => setLightboxOpen(false)}
              className="absolute top-4 right-4 z-10 bg-white/20 hover:bg-white/30 text-white p-2 rounded-full transition-colors"
            >
              <X className="h-6 w-6" />
            </button>

            {/* Photo Counter */}
            <div className="absolute top-4 left-4 z-10 bg-white/20 text-white px-3 py-1 rounded-full text-sm">
              {lightboxIndex + 1} / {lightboxPhotos.length}
            </div>

            {/* Main Image */}
            <div className="flex items-center justify-center min-h-[60vh] p-4">
              {lightboxPhoto && (
                <img
                  src={lightboxPhoto}
                  alt={`Foto ${lightboxIndex + 1}`}
                  className="max-w-full max-h-[80vh] object-contain rounded-lg"
                />
              )}
            </div>

            {/* Navigation Arrows */}
            {lightboxPhotos.length > 1 && (
              <>
                <button
                  onClick={prevPhoto}
                  className="absolute left-4 top-1/2 -translate-y-1/2 bg-white/20 hover:bg-white/30 text-white p-3 rounded-full transition-colors"
                >
                  <ChevronDown className="h-6 w-6 rotate-90" />
                </button>
                <button
                  onClick={nextPhoto}
                  className="absolute right-4 top-1/2 -translate-y-1/2 bg-white/20 hover:bg-white/30 text-white p-3 rounded-full transition-colors"
                >
                  <ChevronDown className="h-6 w-6 -rotate-90" />
                </button>
              </>
            )}

            {/* Thumbnail Strip */}
            {lightboxPhotos.length > 1 && (
              <div className="flex justify-center gap-2 p-4 bg-black/50">
                {lightboxPhotos.map((photo, idx) => (
                  <button
                    key={idx}
                    onClick={() => {
                      setLightboxIndex(idx);
                      setLightboxPhoto(photo);
                    }}
                    className={`w-16 h-16 rounded overflow-hidden border-2 transition-colors ${idx === lightboxIndex ? 'border-orange-500' : 'border-transparent hover:border-white/50'
                      }`}
                  >
                    <img src={photo} alt="" className="w-full h-full object-cover" />
                  </button>
                ))}
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>

      {/* Edit Job Data Dialog */}
      <Dialog open={editJobDialogOpen} onOpenChange={setEditJobDialogOpen}>
        <DialogContent className="max-w-md max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Edit className="h-5 w-5" />
              Daten bearbeiten
            </DialogTitle>
            <DialogDescription>
              Korrigieren Sie Kennzeichen, FIN oder andere Angaben
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
                  <SelectItem value="Fahrzeug ohne gültige Zulassung im öffentlichen Raum">Fahrzeug ohne gültige Zulassung im öffentlichen Raum</SelectItem>
                  <SelectItem value="Fahrzeug ohne Kennzeichen">Fahrzeug ohne Kennzeichen</SelectItem>
                  <SelectItem value="Blockieren einer Feuerwehrzufahrt">Blockieren einer Feuerwehrzufahrt</SelectItem>
                  <SelectItem value="Blockieren von Rettungswegen">Blockieren von Rettungswegen</SelectItem>
                  <SelectItem value="Blockieren von Notausfahrten">Blockieren von Notausfahrten</SelectItem>
                  <SelectItem value="Parken im Sicherheitsbereich von Polizei- oder Feuerwehreinsätzen">Parken im Sicherheitsbereich von Polizei- oder Feuerwehreinsätzen</SelectItem>
                  <SelectItem value="Parken auf einem E-Auto-Ladeplatz ohne Ladevorgang">Parken auf einem E-Auto-Ladeplatz ohne Ladevorgang</SelectItem>
                  <SelectItem value="Parken auf einem Carsharing-Parkplatz ohne Berechtigung">Parken auf einem Carsharing-Parkplatz ohne Berechtigung</SelectItem>
                  <SelectItem value="Parken auf einem Bewohnerparkplatz ohne gültigen Ausweis">Parken auf einem Bewohnerparkplatz ohne gültigen Ausweis</SelectItem>
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
                rows={3}
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
                  key={editJobDialogOpen ? 'edit-map-open' : 'edit-map-closed'}
                >
                  <TileLayer
                    attribution='&copy; OpenStreetMap'
                    url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                  />
                  {editJobPosition && (
                    <Marker position={editJobPosition} />
                  )}
                  <MapClickHandler onMapClick={async (lat, lng) => {
                    setEditJobPosition([lat, lng]);
                    setEditJobData(prev => ({
                      ...prev,
                      location_lat: lat,
                      location_lng: lng
                    }));
                    // Reverse geocoding
                    try {
                      const response = await fetch(
                        `https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lng}`,
                        { headers: { 'User-Agent': 'ImpoundPro/1.0' } }
                      );
                      const data = await response.json();
                      if (data.display_name) {
                        setEditJobData(prev => ({ ...prev, location_address: data.display_name }));
                      }
                    } catch (e) {
                      console.error('Reverse geocoding error:', e);
                    }
                  }} />
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
              {editingJobData ? (
                <>
                  <div className="loading-spinner mr-2"></div>
                  Speichert...
                </>
              ) : (
                <>
                  <Save className="h-4 w-4 mr-2" />
                  Speichern
                </>
              )}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default TowingDashboard;
