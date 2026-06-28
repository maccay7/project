// Mapping Template Manager - Persist mapping configurations with full CRUD via backend API
import api from './api.js'

export const mappingTemplateManager = {
  // Get all mapping templates
  async getAllTemplates() {
    try {
      const response = await api.callAPI('/mapping-templates', 'GET')
      if (response.success) {
        return response.data || []
      }
      return []
    } catch (e) {
      console.error('Error reading mapping templates:', e)
      return []
    }
  },

  // Get templates for a specific instrument type
  async getTemplatesByInstrument(instrumentType) {
    try {
      const response = await api.callAPI(`/mapping-templates?instrument_type=${instrumentType}`, 'GET')
      if (response.success) {
        return response.data || []
      }
      return []
    } catch (e) {
      console.error('Error reading mapping templates by instrument:', e)
      return []
    }
  },

  // Get a specific template by ID
  async getTemplate(id) {
    try {
      const response = await api.callAPI(`/mapping-templates/${id}`, 'GET')
      if (response.success) {
        return response.data
      }
      return null
    } catch (e) {
      console.error('Error loading mapping template:', e)
      return null
    }
  },

  // Save a new mapping template
  async saveTemplate(name, instrumentType, columnMapping, requiredColumns, fileColumns) {
    try {
      const response = await api.callAPI('/mapping-templates', 'POST', {
        name: name.trim(),
        instrument_type: instrumentType,
        column_mapping: columnMapping,
        required_columns: requiredColumns,
        file_columns: fileColumns
      })
      if (response.success) {
        return response.data
      }
      return null
    } catch (e) {
      console.error('Error saving mapping template:', e)
      return null
    }
  },

  // Load a template by ID
  async loadTemplate(id) {
    return await this.getTemplate(id)
  },

  // Rename a template
  async renameTemplate(id, newName) {
    try {
      const response = await api.callAPI(`/mapping-templates/${id}`, 'PUT', {
        name: newName.trim()
      })
      if (response.success) {
        return response.data
      }
      return null
    } catch (e) {
      console.error('Error renaming mapping template:', e)
      return null
    }
  },

  // Update a template
  async updateTemplate(id, updates) {
    try {
      const payload = {}
      if (updates.columnMapping !== undefined) payload.column_mapping = updates.columnMapping
      if (updates.fileColumns !== undefined) payload.file_columns = updates.fileColumns
      if (updates.name !== undefined) payload.name = updates.name
      
      const response = await api.callAPI(`/mapping-templates/${id}`, 'PUT', payload)
      if (response.success) {
        return response.data
      }
      return null
    } catch (e) {
      console.error('Error updating mapping template:', e)
      return null
    }
  },

  // Delete a template
  async deleteTemplate(id) {
    try {
      const response = await api.callAPI(`/mapping-templates/${id}`, 'DELETE')
      return response.success
    } catch (e) {
      console.error('Error deleting mapping template:', e)
      return false
    }
  },

  // Auto-match and save template
  async autoSaveTemplate(instrumentType, columnMapping, requiredColumns, fileColumns) {
    const existing = await this.getTemplatesByInstrument(instrumentType)
    // Check if a similar mapping already exists
    const similar = existing.find(t => {
      const mappingKeys = Object.keys(t.columnMapping || {}).sort()
      const currentKeys = Object.keys(columnMapping || {}).sort()
      return JSON.stringify(mappingKeys) === JSON.stringify(currentKeys)
    })
    
    if (similar) {
      // Update existing similar template
      return await this.updateTemplate(similar.id, {
        columnMapping,
        fileColumns
      })
    }
    
    // Create new auto-generated template
    const autoName = `${instrumentType.replace('-', '_').toUpperCase()}_Auto_${new Date().toISOString().split('T')[0]}`
    return await this.saveTemplate(autoName, instrumentType, columnMapping, requiredColumns, fileColumns)
  },

  // Clear all templates - not implemented for backend
  async clearAllTemplates() {
    console.warn('clearAllTemplates not implemented for backend storage')
    return false
  },

  // Export templates to JSON
  async exportTemplates() {
    const templates = await this.getAllTemplates()
    return JSON.stringify(templates, null, 2)
  },

  // Import templates from JSON - not implemented for backend
  async importTemplates(jsonString) {
    console.warn('importTemplates not implemented for backend storage')
    return []
  }
}

export default mappingTemplateManager
