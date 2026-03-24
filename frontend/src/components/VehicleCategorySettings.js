import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Plus, Edit, Trash2, Save, X, Euro, Car, Truck, Bike } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

// Vordefinierte Kategorien (Hamburg-Modell) als Vorlage
const HAMBURG_TEMPLATES = [
  {
    name: "PKW bis 4t",
    description: "Kraftfahrzeug mit einer zulässigen Gesamtmasse bis 4t oder ein einachsiger Anhänger (normaler PKW)",
    base_price: 135.00,
    daily_rate: 15.00,
    icon: "car"
  },
  {
    name: "LKW 4t - 7,5t",
    description: "Kraftfahrzeug mit einer zulässigen Gesamtmasse über 4t bis 7,5t",
    base_price: 202.00,
    daily_rate: 30.00,
    icon: "truck"
  },
  {
    name: "Fahrrad/Mofa/Moped",
    description: "Fahrrad, Mofa, Moped oder Kleinkraftrad mit Versicherungskennzeichen",
    base_price: 27.00,
    daily_rate: 4.00,
    icon: "bike"
  },
  {
    name: "Kraftrad/Motorrad",
    description: "Kraftrad",
    base_price: 68.00,
    daily_rate: 10.00,
    icon: "bike"
  }
];

const VehicleCategorySettings = ({ onClose }) => {
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editingId, setEditingId] = useState(null);
  const [showAddForm, setShowAddForm] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    base_price: '',
    daily_rate: '',
    is_active: true
  });

  useEffect(() => {
    fetchCategories();
  }, []);

  const fetchCategories = async () => {
    try {
      const response = await axios.get(`${API}/api/vehicle-categories`);
      setCategories(response.data);
    } catch (error) {
      console.error('Error fetching categories:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    if (!formData.name || !formData.base_price || !formData.daily_rate) {
      toast.error('Bitte alle Pflichtfelder ausfüllen');
      return;
    }

    try {
      if (editingId) {
        await axios.put(`${API}/api/vehicle-categories/${editingId}`, {
          ...formData,
          base_price: parseFloat(formData.base_price),
          daily_rate: parseFloat(formData.daily_rate)
        });
        toast.success('Kategorie aktualisiert');
      } else {
        await axios.post(`${API}/api/vehicle-categories`, {
          ...formData,
          base_price: parseFloat(formData.base_price),
          daily_rate: parseFloat(formData.daily_rate)
        });
        toast.success('Kategorie erstellt');
      }
      
      fetchCategories();
      resetForm();
    } catch (error) {
      toast.error('Fehler beim Speichern');
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Kategorie wirklich löschen?')) return;
    
    try {
      await axios.delete(`${API}/api/vehicle-categories/${id}`);
      toast.success('Kategorie gelöscht');
      fetchCategories();
    } catch (error) {
      toast.error('Fehler beim Löschen');
    }
  };

  const handleEdit = (category) => {
    setFormData({
      name: category.name,
      description: category.description || '',
      base_price: category.base_price.toString(),
      daily_rate: category.daily_rate.toString(),
      is_active: category.is_active
    });
    setEditingId(category.id);
    setShowAddForm(true);
  };

  const resetForm = () => {
    setFormData({
      name: '',
      description: '',
      base_price: '',
      daily_rate: '',
      is_active: true
    });
    setEditingId(null);
    setShowAddForm(false);
  };

  const applyTemplate = (template) => {
    setFormData({
      name: template.name,
      description: template.description,
      base_price: template.base_price.toString(),
      daily_rate: template.daily_rate.toString(),
      is_active: true
    });
    setShowAddForm(true);
  };

  const importAllHamburgTemplates = async () => {
    try {
      for (const template of HAMBURG_TEMPLATES) {
        await axios.post(`${API}/api/vehicle-categories`, {
          name: template.name,
          description: template.description,
          base_price: template.base_price,
          daily_rate: template.daily_rate,
          is_active: true
        });
      }
      toast.success('Hamburg-Gebühren importiert!');
      fetchCategories();
    } catch (error) {
      toast.error('Fehler beim Import');
    }
  };

  const getIcon = (name) => {
    const lower = name.toLowerCase();
    if (lower.includes('lkw') || lower.includes('truck')) return <Truck className="h-5 w-5 text-orange-600" />;
    if (lower.includes('fahrrad') || lower.includes('mofa') || lower.includes('kraftrad') || lower.includes('motorrad')) return <Bike className="h-5 w-5 text-green-600" />;
    return <Car className="h-5 w-5 text-blue-600" />;
  };

  return (
    <div className="bg-white rounded-lg shadow-lg max-w-4xl w-full max-h-[90vh] overflow-y-auto">
      {/* Header */}
      <div className="sticky top-0 bg-white border-b px-6 py-4 flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-slate-900">Fahrzeugkategorien & Gebühren</h2>
          <p className="text-sm text-slate-500">Verwalten Sie Ihre Preiskategorien für verschiedene Fahrzeugtypen</p>
        </div>
        {onClose && (
          <button onClick={onClose} className="p-2 hover:bg-slate-100 rounded-lg">
            <X className="h-5 w-5" />
          </button>
        )}
      </div>

      <div className="p-6 space-y-6">
        {/* Hamburg-Vorlage importieren */}
        {categories.length === 0 && !loading && (
          <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
            <h3 className="font-semibold text-amber-800 mb-2">🏛️ Hamburg-Gebührenordnung importieren?</h3>
            <p className="text-sm text-amber-700 mb-3">
              Importieren Sie die offiziellen Hamburger Verwahrgebühren als Vorlage.
            </p>
            <button
              onClick={importAllHamburgTemplates}
              className="bg-amber-600 text-white px-4 py-2 rounded-lg hover:bg-amber-700 text-sm font-medium"
            >
              Hamburg-Gebühren importieren
            </button>
          </div>
        )}

        {/* Vorlagen-Buttons */}
        {showAddForm && !editingId && (
          <div className="bg-slate-50 rounded-lg p-4">
            <p className="text-sm text-slate-600 mb-3">Schnellauswahl (Vorlage):</p>
            <div className="flex flex-wrap gap-2">
              {HAMBURG_TEMPLATES.map((t, i) => (
                <button
                  key={i}
                  onClick={() => applyTemplate(t)}
                  className="px-3 py-1.5 bg-white border border-slate-200 rounded-lg text-sm hover:bg-slate-100 flex items-center gap-2"
                >
                  {getIcon(t.name)}
                  {t.name}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Add/Edit Form */}
        {showAddForm && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 space-y-4">
            <h3 className="font-semibold text-blue-900">
              {editingId ? 'Kategorie bearbeiten' : 'Neue Kategorie hinzufügen'}
            </h3>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Kategoriename *
                </label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="z.B. PKW bis 4t"
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
              
              <div className="md:col-span-2">
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Beschreibung
                </label>
                <input
                  type="text"
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  placeholder="z.B. Kraftfahrzeug mit einer zulässigen Gesamtmasse bis 4t"
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Grundpreis (erste 24h) *
                </label>
                <div className="relative">
                  <input
                    type="number"
                    step="0.01"
                    value={formData.base_price}
                    onChange={(e) => setFormData({ ...formData, base_price: e.target.value })}
                    placeholder="135.00"
                    className="w-full px-3 py-2 pr-8 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                  <Euro className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
                </div>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Tagessatz (weitere 24h) *
                </label>
                <div className="relative">
                  <input
                    type="number"
                    step="0.01"
                    value={formData.daily_rate}
                    onChange={(e) => setFormData({ ...formData, daily_rate: e.target.value })}
                    placeholder="15.00"
                    className="w-full px-3 py-2 pr-8 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                  <Euro className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
                </div>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="is_active"
                checked={formData.is_active}
                onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                className="rounded border-slate-300"
              />
              <label htmlFor="is_active" className="text-sm text-slate-700">Aktiv</label>
            </div>

            <div className="flex gap-2">
              <button
                onClick={handleSave}
                className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 flex items-center gap-2"
              >
                <Save className="h-4 w-4" />
                Speichern
              </button>
              <button
                onClick={resetForm}
                className="bg-slate-200 text-slate-700 px-4 py-2 rounded-lg hover:bg-slate-300"
              >
                Abbrechen
              </button>
            </div>
          </div>
        )}

        {/* Add Button */}
        {!showAddForm && (
          <button
            onClick={() => setShowAddForm(true)}
            className="w-full py-3 border-2 border-dashed border-slate-300 rounded-lg text-slate-600 hover:border-blue-400 hover:text-blue-600 hover:bg-blue-50 transition-colors flex items-center justify-center gap-2"
          >
            <Plus className="h-5 w-5" />
            Neue Kategorie hinzufügen
          </button>
        )}

        {/* Categories List */}
        {loading ? (
          <div className="text-center py-8 text-slate-500">Laden...</div>
        ) : categories.length === 0 ? (
          <div className="text-center py-8 text-slate-500">
            Noch keine Kategorien angelegt
          </div>
        ) : (
          <div className="space-y-3">
            <h3 className="font-semibold text-slate-700">Ihre Kategorien ({categories.length})</h3>
            {categories.map((cat) => (
              <div
                key={cat.id}
                className={`border rounded-lg p-4 ${cat.is_active ? 'bg-white' : 'bg-slate-50 opacity-60'}`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-start gap-3">
                    {getIcon(cat.name)}
                    <div>
                      <h4 className="font-semibold text-slate-900">{cat.name}</h4>
                      {cat.description && (
                        <p className="text-sm text-slate-500 mt-0.5">{cat.description}</p>
                      )}
                      <div className="flex gap-4 mt-2 text-sm">
                        <span className="text-green-700 font-medium">
                          Grundpreis: {cat.base_price.toFixed(2)} €
                        </span>
                        <span className="text-blue-700">
                          + {cat.daily_rate.toFixed(2)} €/24h
                        </span>
                      </div>
                      {!cat.is_active && (
                        <span className="inline-block mt-2 px-2 py-0.5 bg-slate-200 text-slate-600 text-xs rounded">
                          Deaktiviert
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => handleEdit(cat)}
                      className="p-2 hover:bg-slate-100 rounded-lg text-slate-600"
                      title="Bearbeiten"
                    >
                      <Edit className="h-4 w-4" />
                    </button>
                    <button
                      onClick={() => handleDelete(cat.id)}
                      className="p-2 hover:bg-red-50 rounded-lg text-red-600"
                      title="Löschen"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Rechenbeispiel */}
        {categories.length > 0 && (
          <div className="bg-slate-50 rounded-lg p-4">
            <h4 className="font-semibold text-slate-700 mb-2">📊 Rechenbeispiel</h4>
            <p className="text-sm text-slate-600">
              Bei <strong>{categories[0]?.name}</strong> und 3 Tagen Standzeit:
            </p>
            <p className="text-sm text-slate-800 mt-1">
              {categories[0]?.base_price.toFixed(2)} € (erste 24h) + 2 × {categories[0]?.daily_rate.toFixed(2)} € = 
              <strong className="text-green-700 ml-1">
                {(categories[0]?.base_price + 2 * categories[0]?.daily_rate).toFixed(2)} €
              </strong>
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

export default VehicleCategorySettings;
