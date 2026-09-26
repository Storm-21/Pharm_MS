import React, { useCallback, useEffect, useState } from 'react';
import { apiClient } from '../api';
import { AlertCircle, Plus, Loader2, Pencil, Trash2, MapPin, X, Minus } from 'lucide-react';

export function InventoryManagement() {
  const [inventory, setInventory] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(false);
  const [statusFilter, setStatusFilter] = useState('');
  const [showAddModal, setShowAddModal] = useState(false);
  const [formData, setFormData] = useState({
    medicine_id: '',
    quantity_in_stock: '',
    reorder_level: '20',
    max_stock: '500',
    batch_number: '',
    manufacturing_date: '',
    expiry_date: '',
    storage_location: '',
  });

  // Declared with useCallback and before the effect that calls them: defining
  // these after the effect and omitting them from the dependency array left the
  // request closures capturing a stale statusFilter, so changing the filter
  // could render the previous filter's rows.
  const fetchInventory = useCallback(async () => {
    setLoading(true);
    try {
      const response = await apiClient.getInventory(statusFilter);
      setInventory((response && response.data) || []);
    } catch (error) {
      console.error('Error fetching inventory:', error);
      setInventory([]);
    } finally {
      setLoading(false);
    }
  }, [statusFilter]);

  const fetchAlerts = useCallback(async () => {
    try {
      const [alertsRes, summaryRes] = await Promise.all([
        apiClient.getStockAlerts(),
        apiClient.getInventorySummary(),
      ]);
      setAlerts((alertsRes && alertsRes.data) || []);
      setSummary((summaryRes && summaryRes.data) || null);
    } catch (error) {
      console.error('Error fetching alerts:', error);
    }
  }, []);

  useEffect(() => {
    fetchInventory();
    fetchAlerts();
    fetchSummary();
  }, [fetchInventory, fetchAlerts, fetchSummary]);

  const handleAddInventory = async (e) => {
    e.preventDefault();
    try {
      await apiClient.createInventory(formData);
      setShowAddModal(false);
      setFormData({
        medicine_id: '',
        quantity_in_stock: '',
        reorder_level: '20',
        max_stock: '500',
        batch_number: '',
        manufacturing_date: '',
        expiry_date: '',
        storage_location: '',
      });
      fetchInventory();
    } catch (error) {
      console.error('Error adding inventory:', error);
      alert('Error adding inventory: ' + error.message);
    }
  };

  const handleStockUpdate = async (itemId, change) => {
    try {
      await apiClient.updateInventoryStock(itemId, change);
      refresh();
    } catch (error) {
      console.error('Error updating stock:', error);
      alert('Error updating stock');
    }
  };

  const fetchSummary = useCallback(async () => {
    try {
      const response = await apiClient.getInventorySummary();
      setSummary(response.data);
    } catch (error) {
      console.error('Error fetching summary:', error);
    }
  }, []);

  // --- Free-panel state -----------------------------------------------------
  // editing: the inventory row being edited (edit drawer open when non-null)
  // editForm: its editable fields
  // stockEntry: { id, amount, mode } for the free quantity add/remove panel
  const [editing, setEditing] = useState(null);
  const [editForm, setEditForm] = useState(null);
  const [stockEntry, setStockEntry] = useState(null);
  const [deleteTarget, setDeleteTarget] = useState(null);

  const refresh = useCallback(() => {
    fetchInventory();
    fetchAlerts();
    fetchSummary();
  }, [fetchInventory, fetchAlerts, fetchSummary]);

  const openEdit = (item) => {
    setEditing(item);
    setEditForm({
      quantity_in_stock: item.quantity_in_stock,
      reorder_level: item.reorder_level,
      max_stock: item.max_stock,
      batch_number: item.batch_number,
      manufacturing_date: item.manufacturing_date || '',
      expiry_date: item.expiry_date || '',
      storage_location: item.storage_location || '',
    });
  };

  const handleEditSave = async () => {
    try {
      await apiClient.updateInventory(editing.id, editForm);
      setEditing(null);
      setEditForm(null);
      refresh();
    } catch (error) {
      console.error('Error saving inventory item:', error);
      alert('Error saving changes');
    }
  };

  const handleDelete = async () => {
    try {
      await apiClient.deleteInventory(deleteTarget.id);
      setDeleteTarget(null);
      refresh();
    } catch (error) {
      console.error('Error deleting inventory item:', error);
      alert('Error deleting stock line');
    }
  };

  const handleStockEntry = async () => {
    const amount = Math.abs(parseInt(stockEntry.amount, 10) || 0);
    if (!amount) return;
    try {
      await apiClient.updateInventoryStock(
        stockEntry.id, stockEntry.mode === 'remove' ? -amount : amount);
      setStockEntry(null);
      refresh();
    } catch (error) {
      console.error('Error updating stock:', error);
      alert('Error updating stock');
    }
  };

  // Inline shelf-location edit. Commits on blur or Enter, so a pharmacist can
  // tab down the column relabelling shelves without opening any drawer.
  const [locationDrafts, setLocationDrafts] = useState({});
  const handleLocationChange = (id, value) =>
    setLocationDrafts((d) => ({ ...d, [id]: value }));
  const handleLocationCommit = async (item) => {
    const value = locationDrafts[item.id];
    if (value === undefined) return;
    setLocationDrafts((d) => {
      const next = { ...d };
      delete next[item.id];
      return next;
    });
    if (value === (item.storage_location || '')) return;
    try {
      await apiClient.updateInventory(item.id, { storage_location: value });
      fetchInventory();
    } catch (error) {
      console.error('Error updating location:', error);
      alert('Error updating location');
    }
  };

  const getStatusBadge = (status) => {
    const colors = {
      in_stock: 'bg-green-100 text-green-800',
      low_stock: 'bg-yellow-100 text-yellow-800',
      out_of_stock: 'bg-red-100 text-red-800',
      expired: 'bg-gray-100 text-gray-800',
    };
    return colors[status] || 'bg-gray-100 text-gray-800';
  };

  const getAlertColor = (type) => {
    switch (type) {
      case 'OUT_OF_STOCK':
        return 'bg-red-50 border-l-4 border-red-500';
      case 'LOW_STOCK':
        return 'bg-yellow-50 border-l-4 border-yellow-500';
      case 'EXPIRED':
        return 'bg-gray-50 border-l-4 border-gray-500';
      default:
        return 'bg-blue-50 border-l-4 border-blue-500';
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold text-gray-800">Inventory Management</h1>
        <button
          onClick={() => setShowAddModal(true)}
          className="bg-blue-600 text-white px-4 py-2 rounded-lg flex items-center gap-2 hover:bg-blue-700"
        >
          <Plus className="w-5 h-5" />
          Add Stock
        </button>
      </div>

      {/* Stock value summary */}
      {summary && (
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          <div className="rounded-lg bg-white p-4 shadow">
            <p className="text-xs uppercase tracking-wide text-gray-500">Stock lines</p>
            <p className="text-2xl font-bold text-gray-800">{summary.total_lines}</p>
          </div>
          <div className="rounded-lg bg-white p-4 shadow">
            <p className="text-xs uppercase tracking-wide text-gray-500">Total units</p>
            <p className="text-2xl font-bold text-gray-800">{summary.total_units}</p>
          </div>
          <div className="rounded-lg bg-white p-4 shadow">
            <p className="text-xs uppercase tracking-wide text-gray-500">Value at cost</p>
            <p className="text-2xl font-bold text-gray-800">
              \u20b9{summary.stock_value_at_cost.toLocaleString('en-IN')}
            </p>
          </div>
          <div className="rounded-lg bg-white p-4 shadow">
            <p className="text-xs uppercase tracking-wide text-gray-500">Value at retail</p>
            <p className="text-2xl font-bold text-gray-800">
              \u20b9{summary.stock_value_at_retail.toLocaleString('en-IN')}
            </p>
          </div>
        </div>
      )}

      {/* Stock Alerts */}
      {alerts.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-lg font-semibold flex items-center gap-2 text-orange-600">
            <AlertCircle className="w-5 h-5" />
            Stock Alerts
          </h2>
          {alerts.map((alert, index) => (
            <div key={index} className={`${getAlertColor(alert.type)} p-4 rounded-lg`}>
              <p className="font-semibold text-gray-900">{alert.medicine_name}</p>
              <p className="text-sm text-gray-700 mt-1">
                {alert.type === 'OUT_OF_STOCK' && 'Stock depleted - Immediate reorder required'}
                {alert.type === 'LOW_STOCK' && `Current stock: ${alert.current_stock} (Reorder level: ${alert.reorder_level})`}
                {alert.type === 'EXPIRED' && `Expired on ${alert.expiry_date}`}
              </p>
            </div>
          ))}
        </div>
      )}

      {/* Status Filter */}
      <div className="flex gap-2 flex-wrap">
        <button
          onClick={() => setStatusFilter('')}
          className={`px-4 py-2 rounded-lg transition ${
            statusFilter === ''
              ? 'bg-blue-600 text-white'
              : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
          }`}
        >
          All
        </button>
        <button
          onClick={() => setStatusFilter('in_stock')}
          className={`px-4 py-2 rounded-lg transition ${
            statusFilter === 'in_stock'
              ? 'bg-green-600 text-white'
              : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
          }`}
        >
          In Stock
        </button>
        <button
          onClick={() => setStatusFilter('low_stock')}
          className={`px-4 py-2 rounded-lg transition ${
            statusFilter === 'low_stock'
              ? 'bg-yellow-600 text-white'
              : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
          }`}
        >
          Low Stock
        </button>
        <button
          onClick={() => setStatusFilter('out_of_stock')}
          className={`px-4 py-2 rounded-lg transition ${
            statusFilter === 'out_of_stock'
              ? 'bg-red-600 text-white'
              : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
          }`}
        >
          Out of Stock
        </button>
        <button
          onClick={() => setStatusFilter('expired')}
          className={`px-4 py-2 rounded-lg transition ${
            statusFilter === 'expired'
              ? 'bg-gray-600 text-white'
              : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
          }`}
        >
          Expired
        </button>
      </div>

      {/* Inventory Table */}
      <div className="bg-white rounded-lg shadow overflow-x-auto">
        {loading ? (
          <div className="flex items-center justify-center p-8 text-gray-500">
            <Loader2 className="mr-2 h-5 w-5 animate-spin" /> Loading inventory...
          </div>
        ) : inventory.length === 0 ? (
          <div className="p-8 text-center text-gray-500">No inventory items found</div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-100 border-b">
              <tr>
                <th className="px-4 py-3 text-left font-semibold text-gray-700">Medicine</th>
                <th className="px-4 py-3 text-left font-semibold text-gray-700">Batch #</th>
                <th className="px-4 py-3 text-center font-semibold text-gray-700">Stock</th>
                <th className="px-4 py-3 text-center font-semibold text-gray-700">Reorder Level</th>
                <th className="px-4 py-3 text-left font-semibold text-gray-700">Expiry Date</th>
                <th className="px-4 py-3 text-left font-semibold text-gray-700">Location</th>
                <th className="px-4 py-3 text-center font-semibold text-gray-700">Status</th>
                <th className="px-4 py-3 text-center font-semibold text-gray-700">Actions</th>
              </tr>
            </thead>
            <tbody>
              {inventory.map((item) => (
                <tr key={item.id} className="border-b hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <div className="text-gray-900 font-medium">{item.medicine_name}</div>
                    {item.manufacturer && (
                      <div className="text-xs text-gray-500">{item.manufacturer}</div>
                    )}
                  </td>
                  <td className="px-4 py-3 text-gray-600">{item.batch_number}</td>
                  <td className="px-4 py-3 text-center text-gray-900 font-semibold">{item.quantity_in_stock}</td>
                  <td className="px-4 py-3 text-center text-gray-600">{item.reorder_level}</td>
                  <td className="px-4 py-3 text-gray-600">{item.expiry_date}</td>
                  <td className="px-4 py-3">
                    {/* Editable at will, as asked: click the cell, type the
                        shelf, press Enter or click away, it saves. */}
                    <input
                      type="text"
                      defaultValue={item.storage_location || ''}
                      value={locationDrafts[item.id] ?? undefined}
                      onChange={(e) => handleLocationChange(item.id, e.target.value)}
                      onBlur={() => handleLocationCommit(item)}
                      onKeyDown={(e) => { if (e.key === 'Enter') e.target.blur(); }}
                      placeholder="e.g., Shelf A1"
                      className="w-28 px-2 py-1 border border-transparent rounded hover:border-gray-300 focus:border-blue-500 focus:outline-none text-sm text-gray-600 bg-gray-50 focus:bg-white"
                      title="Click to edit where this medicine is kept"
                    />
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span className={`px-2 py-1 rounded text-xs font-semibold ${getStatusBadge(item.status)}`}>
                      {item.status.replace('_', ' ').toUpperCase()}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-center space-x-1 whitespace-nowrap">
                    <button
                      onClick={() => handleStockUpdate(item.id, 10)}
                      className="px-2 py-1 bg-green-100 text-green-700 rounded text-xs hover:bg-green-200"
                      title="Add 10 units"
                    >
                      +10
                    </button>
                    <button
                      onClick={() => handleStockUpdate(item.id, -5)}
                      className="px-2 py-1 bg-red-100 text-red-700 rounded text-xs hover:bg-red-200"
                      title="Remove 5 units"
                    >
                      -5
                    </button>
                    <button
                      onClick={() => setStockEntry({ id: item.id, name: item.medicine_name, amount: '', mode: 'add' })}
                      className="px-2 py-1 bg-blue-100 text-blue-700 rounded text-xs hover:bg-blue-200"
                      title="Add or remove any amount"
                    >
                      ± Qty
                    </button>
                    <button
                      onClick={() => openEdit(item)}
                      className="px-2 py-1 bg-gray-100 text-gray-700 rounded hover:bg-gray-200"
                      title="Edit details, batch, expiry or location"
                    >
                      <Pencil className="w-3.5 h-3.5" />
                    </button>
                    <button
                      onClick={() => setDeleteTarget(item)}
                      className="px-2 py-1 bg-red-100 text-red-700 rounded hover:bg-red-200"
                      title="Remove this stock line"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Add Inventory Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto p-6">
            <h2 className="text-2xl font-bold mb-6">Add Stock</h2>

            <form onSubmit={handleAddInventory} className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Medicine ID *</label>
                  <input
                    type="number"
                    required
                    value={formData.medicine_id}
                    onChange={(e) => setFormData({...formData, medicine_id: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Quantity *</label>
                  <input
                    type="number"
                    required
                    value={formData.quantity_in_stock}
                    onChange={(e) => setFormData({...formData, quantity_in_stock: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Reorder Level</label>
                  <input
                    type="number"
                    value={formData.reorder_level}
                    onChange={(e) => setFormData({...formData, reorder_level: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Max Stock</label>
                  <input
                    type="number"
                    value={formData.max_stock}
                    onChange={(e) => setFormData({...formData, max_stock: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Batch Number *</label>
                  <input
                    type="text"
                    required
                    value={formData.batch_number}
                    onChange={(e) => setFormData({...formData, batch_number: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Manufacturing Date *</label>
                  <input
                    type="date"
                    required
                    value={formData.manufacturing_date}
                    onChange={(e) => setFormData({...formData, manufacturing_date: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Expiry Date *</label>
                  <input
                    type="date"
                    required
                    value={formData.expiry_date}
                    onChange={(e) => setFormData({...formData, expiry_date: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Storage Location</label>
                  <input
                    type="text"
                    value={formData.storage_location}
                    onChange={(e) => setFormData({...formData, storage_location: e.target.value})}
                    placeholder="e.g., Shelf A1"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>

              <div className="flex justify-end gap-3 mt-6">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                >
                  Add Stock
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Free quantity panel: any amount, add or remove, named so the
          pharmacist can see at a glance WHICH line is being changed. */}
      {stockEntry && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg w-full max-w-sm p-6">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-lg font-bold">Adjust stock</h2>
              <button onClick={() => setStockEntry(null)} className="text-gray-400 hover:text-gray-600">
                <X className="w-5 h-5" />
              </button>
            </div>
            <p className="text-sm text-gray-600 mb-4">
              {stockEntry.mode === 'remove' ? 'Remove from' : 'Add to'} <span className="font-semibold">{stockEntry.name}</span>
            </p>
            <div className="flex gap-2 mb-4">
              <button
                onClick={() => setStockEntry({ ...stockEntry, mode: 'add' })}
                className={`flex-1 py-2 rounded-lg flex items-center justify-center gap-1 font-medium ${stockEntry.mode === 'add' ? 'bg-green-600 text-white' : 'bg-gray-100 text-gray-600'}`}
              >
                <Plus className="w-4 h-4" /> Add
              </button>
              <button
                onClick={() => setStockEntry({ ...stockEntry, mode: 'remove' })}
                className={`flex-1 py-2 rounded-lg flex items-center justify-center gap-1 font-medium ${stockEntry.mode === 'remove' ? 'bg-red-600 text-white' : 'bg-gray-100 text-gray-600'}`}
              >
                <Minus className="w-4 h-4" /> Remove
              </button>
            </div>
            <input
              type="number"
              min="1"
              autoFocus
              placeholder="Amount"
              value={stockEntry.amount}
              onChange={(e) => setStockEntry({ ...stockEntry, amount: e.target.value })}
              onKeyDown={(e) => { if (e.key === 'Enter') handleStockEntry(); }}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 mb-4"
            />
            <div className="flex gap-2 mb-4">
              {[1, 5, 10, 50, 100].map((n) => (
                <button
                  key={n}
                  onClick={() => setStockEntry({ ...stockEntry, amount: String(n) })}
                  className="flex-1 py-1 text-sm bg-gray-100 hover:bg-gray-200 rounded"
                >
                  {n}
                </button>
              ))}
            </div>
            <button
              onClick={handleStockEntry}
              disabled={!stockEntry.amount}
              className={`w-full py-2 rounded-lg font-medium text-white disabled:opacity-40 ${stockEntry.mode === 'remove' ? 'bg-red-600 hover:bg-red-700' : 'bg-green-600 hover:bg-green-700'}`}
            >
              {stockEntry.mode === 'remove' ? 'Remove' : 'Add'} {stockEntry.amount || ''} units
            </button>
          </div>
        </div>
      )}

      {/* Edit drawer: modify any detail of a stock line - batch, dates,
          levels and where it is kept. */}
      {editing && editForm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg max-w-xl w-full max-h-[90vh] overflow-y-auto p-6">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-bold">Edit stock line</h2>
              <button onClick={() => { setEditing(null); setEditForm(null); }} className="text-gray-400 hover:text-gray-600">
                <X className="w-5 h-5" />
              </button>
            </div>
            <p className="text-sm text-gray-500 mb-6">{editing.medicine_name}</p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Quantity in stock</label>
                <input type="number" value={editForm.quantity_in_stock}
                  onChange={(e) => setEditForm({ ...editForm, quantity_in_stock: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Batch number</label>
                <input type="text" value={editForm.batch_number}
                  onChange={(e) => setEditForm({ ...editForm, batch_number: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Reorder level</label>
                <input type="number" value={editForm.reorder_level}
                  onChange={(e) => setEditForm({ ...editForm, reorder_level: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Max stock</label>
                <input type="number" value={editForm.max_stock}
                  onChange={(e) => setEditForm({ ...editForm, max_stock: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Manufacturing date</label>
                <input type="date" value={editForm.manufacturing_date}
                  onChange={(e) => setEditForm({ ...editForm, manufacturing_date: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Expiry date</label>
                <input type="date" value={editForm.expiry_date}
                  onChange={(e) => setEditForm({ ...editForm, expiry_date: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" />
              </div>
              <div className="md:col-span-2">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  <span className="inline-flex items-center gap-1"><MapPin className="w-4 h-4" /> Storage location</span>
                </label>
                <input type="text" value={editForm.storage_location} placeholder="e.g., Shelf A1, cold storage, counter drawer"
                  onChange={(e) => setEditForm({ ...editForm, storage_location: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" />
              </div>
            </div>
            <div className="flex justify-end gap-2 mt-6">
              <button onClick={() => { setEditing(null); setEditForm(null); }}
                className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300">
                Cancel
              </button>
              <button onClick={handleEditSave}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
                Save changes
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete confirmation: removing a stock line is not undoable, so it is
          named and confirmed rather than a bare click. */}
      {deleteTarget && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg max-w-sm w-full p-6">
            <h2 className="text-lg font-bold mb-2">Remove stock line</h2>
            <p className="text-sm text-gray-600 mb-6">
              Delete <span className="font-semibold">{deleteTarget.medicine_name}</span> (batch {deleteTarget.batch_number}, {deleteTarget.quantity_in_stock} units)? This cannot be undone.
            </p>
            <div className="flex justify-end gap-2">
              <button onClick={() => setDeleteTarget(null)}
                className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300">
                Cancel
              </button>
              <button onClick={handleDelete}
                className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700">
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
