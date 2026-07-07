<template>
  <div class="excel-viewer-overlay" v-if="visible">
    <div class="excel-viewer-modal">
      <!-- Header with Logo -->
      <div class="viewer-header">
        <div class="header-left">
          <img src="/DuraCapital logo.png" alt="DuraCapital" class="logo" />
          <h3>{{ fileName || 'Excel Viewer' }}</h3>
        </div>
        <button class="close-btn" @click="closeViewer">✕</button>
      </div>

      <!-- Sheet Tabs -->
      <div class="sheet-tabs" v-if="sheetNames.length > 0">
        <div
          v-for="sheet in sheetNames"
          :key="sheet"
          class="sheet-tab"
          :class="{ active: activeSheet === sheet }"
          @click="switchSheet(sheet)"
        >
          {{ sheet }}
        </div>
      </div>

      <!-- Data Grid -->
      <div class="table-wrapper" v-if="displayedData.length > 0">
        <table class="data-grid">
          <thead>
            <tr>
              <th v-for="(col, idx) in columns" :key="idx">
                {{ col }}
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, rowIdx) in displayedData" :key="rowIdx">
              <td v-for="(col, colIdx) in columns" :key="colIdx">
                {{ formatCell(row[col]) }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Pagination -->
      <div class="pagination-wrapper" v-if="fullData.length > pageSize">
        <button class="page-btn" :disabled="currentPage === 0" @click="prevPage">◀ Prev</button>
        <span class="page-info">Page {{ currentPage + 1 }} of {{ totalPages }}</span>
        <button class="page-btn" :disabled="currentPage >= totalPages - 1" @click="nextPage">Next ▶</button>
        <button class="load-all-btn" @click="loadAllRows">Load All ({{ fullData.length }} rows)</button>
      </div>

      <div v-else class="empty-state">
        <p>No data found in this sheet.</p>
      </div>
    </div>
  </div>
</template>

<script>
import * as XLSX from 'xlsx';

export default {
  name: 'ExcelModalViewer',
  props: {
    visible: {
      type: Boolean,
      default: false
    },
    fileData: {
      type: Object,
      default: null
    }
  },
  data() {
    return {
      fileName: '',
      workbook: null,
      sheetNames: [],
      activeSheet: '',
      fullData: [],
      displayedData: [],
      columns: [],
      pageSize: 100,
      currentPage: 0,
      totalPages: 0
    };
  },
  watch: {
    visible(newVal) {
      if (newVal && this.fileData) {
        this.loadFileData(this.fileData);
      }
    },
    fileData: {
      handler(newVal) {
        if (this.visible && newVal) {
          this.loadFileData(newVal);
        }
      },
      deep: true
    }
  },
  methods: {
    loadFileData(fileData) {
      try {
        console.log('📂 Loading file data into viewer...');
        
        if (fileData.name) {
          this.fileName = fileData.name;
        }

        // 1) If we have an arrayBuffer (original file buffer)
        if (fileData.arrayBuffer) {
          console.log('📄 Parsing original file arrayBuffer...');
          this.workbook = XLSX.read(fileData.arrayBuffer, { type: 'array' });
        }
        // 2) If we have base64 data
        else if (fileData.base64) {
          console.log('📄 Parsing base64 data...');
          const binary = atob(fileData.base64.split(',')[1]);
          const arrayBuffer = new ArrayBuffer(binary.length);
          const uint8Array = new Uint8Array(arrayBuffer);
          for (let i = 0; i < binary.length; i++) {
            uint8Array[i] = binary.charCodeAt(i);
          }
          this.workbook = XLSX.read(arrayBuffer, { type: 'array' });
        }
        // 3) If we have a File object
        else if (fileData instanceof File) {
          console.log('📄 Processing File object...');
          const reader = new FileReader();
          reader.onload = (e) => {
            const data = new Uint8Array(e.target.result);
            this.workbook = XLSX.read(data, { type: 'array' });
            this.afterLoad();
          };
          reader.readAsArrayBuffer(fileData);
          return;
        }
        // 4) If we already have parsed workbook data (sheets array)
        else if (fileData.sheets && Array.isArray(fileData.sheets)) {
          console.log('📄 Using pre-parsed workbook sheets...');
          // Convert to a structure that afterLoad understands
          this.workbook = {
            sheets: fileData.sheets,
            SheetNames: fileData.sheets.map(s => s.name)
          };
        }
        // 5) If we have a data URL
        else if (typeof fileData === 'string' && fileData.startsWith('data:')) {
          console.log('📄 Parsing data URL...');
          const binary = atob(fileData.split(',')[1]);
          const arrayBuffer = new ArrayBuffer(binary.length);
          const uint8Array = new Uint8Array(arrayBuffer);
          for (let i = 0; i < binary.length; i++) {
            uint8Array[i] = binary.charCodeAt(i);
          }
          this.workbook = XLSX.read(arrayBuffer, { type: 'array' });
        }
        // Fallback: assume it's already a workbook
        else {
          console.log('📄 Assuming workbook is already loaded...');
          this.workbook = fileData;
        }

        this.afterLoad();
      } catch (error) {
        console.error('❌ Error loading file data:', error);
        alert('Failed to load Excel file. Please check the format.');
      }
    },

    afterLoad() {
      if (this.workbook) {
        // Handle both XLSX workbook and our custom sheets format
        if (this.workbook.SheetNames) {
          this.sheetNames = this.workbook.SheetNames || [];
        } else if (this.workbook.sheets && Array.isArray(this.workbook.sheets)) {
          this.sheetNames = this.workbook.sheets.map(s => s.name);
        } else {
          this.sheetNames = [];
        }
        
        console.log('📑 Sheets found:', this.sheetNames);
        if (this.sheetNames.length > 0) {
          this.switchSheet(this.sheetNames[0]);
        }
      }
    },

    switchSheet(sheetName) {
      this.activeSheet = sheetName;
      this.currentPage = 0;
      this.loadSheetData(sheetName);
    },

    loadSheetData(sheetName) {
      let data = [];
      
      // Handle XLSX workbook format
      if (this.workbook.Sheets && this.workbook.Sheets[sheetName]) {
        const worksheet = this.workbook.Sheets[sheetName];
        // Use sheet_to_json with raw: false to preserve formatting
        data = XLSX.utils.sheet_to_json(worksheet, { defval: '', raw: false });
      }
      // Handle our custom sheets format
      else if (this.workbook.sheets && Array.isArray(this.workbook.sheets)) {
        const sheet = this.workbook.sheets.find(s => s.name === sheetName);
        if (sheet) {
          data = sheet.data || [];
        }
      }
      
      this.fullData = data;
      
      if (this.fullData.length > 0) {
        this.columns = Object.keys(this.fullData[0]);
      } else {
        this.columns = [];
      }

      this.totalPages = Math.ceil(this.fullData.length / this.pageSize);
      this.currentPage = 0;
      this.updateDisplayGrid();

      console.log(`📊 Sheet "${sheetName}" loaded. Total rows: ${this.fullData.length}`);
    },

    updateDisplayGrid() {
      const start = this.currentPage * this.pageSize;
      const end = Math.min(start + this.pageSize, this.fullData.length);
      this.displayedData = this.fullData.slice(start, end);
    },

    nextPage() {
      if (this.currentPage < this.totalPages - 1) {
        this.currentPage++;
        this.updateDisplayGrid();
        this.scrollToTop();
      }
    },

    prevPage() {
      if (this.currentPage > 0) {
        this.currentPage--;
        this.updateDisplayGrid();
        this.scrollToTop();
      }
    },

    loadAllRows() {
      this.currentPage = 0;
      this.pageSize = this.fullData.length;
      this.totalPages = 1;
      this.updateDisplayGrid();
    },

    scrollToTop() {
      const wrapper = this.$el.querySelector('.table-wrapper');
      if (wrapper) wrapper.scrollTop = 0;
    },

    formatCell(value) {
      if (value === null || value === undefined || value === '') return '';
      return value;
    },

    closeViewer() {
      this.$emit('close');
      this.$emit('update:visible', false);
      this.displayedData = [];
      this.fullData = [];
      this.columns = [];
      this.pageSize = 100;
    }
  }
};
</script>

<style scoped>
.excel-viewer-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.6);
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.excel-viewer-modal {
  background: white;
  border-radius: 12px;
  max-width: 95%;
  max-height: 90vh;
  width: 1400px;
  display: flex;
  flex-direction: column;
  box-shadow: 0 25px 60px rgba(0, 0, 0, 0.3);
  overflow: hidden;
}

.viewer-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  background: #f8f9fa;
  border-bottom: 2px solid #e9ecef;
  flex-shrink: 0;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.logo {
  height: 40px;
  width: auto;
  object-fit: contain;
}

.viewer-header h3 {
  margin: 0;
  font-size: 18px;
  color: #2c3e50;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.close-btn {
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  color: #6c757d;
  padding: 0 8px;
  line-height: 1;
}

.close-btn:hover {
  color: #dc3545;
}

.sheet-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  padding: 10px 20px;
  background: #f1f3f5;
  border-bottom: 2px solid #e9ecef;
  flex-shrink: 0;
  max-height: 80px;
  overflow-y: auto;
}

.sheet-tab {
  padding: 6px 16px;
  background: #e9ecef;
  border-radius: 4px 4px 0 0;
  cursor: pointer;
  font-size: 13px;
  font-weight: 500;
  transition: all 0.2s;
  white-space: nowrap;
}

.sheet-tab:hover {
  background: #dee2e6;
}

.sheet-tab.active {
  background: #007bff;
  color: white;
}

.table-wrapper {
  flex: 1;
  overflow: auto;
  padding: 0 20px 20px 20px;
  max-height: 500px;
}

.data-grid {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.data-grid th {
  background: #f8f9fa;
  padding: 8px 10px;
  border: 1px solid #dee2e6;
  text-align: left;
  position: sticky;
  top: 0;
  z-index: 10;
  font-weight: 600;
  white-space: nowrap;
}

.data-grid td {
  padding: 6px 10px;
  border: 1px solid #e9ecef;
  white-space: nowrap;
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
}

.data-grid tr:nth-child(even) {
  background: #fafafa;
}

.data-grid tr:hover {
  background: #e8f0fe;
}

.pagination-wrapper {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 15px;
  padding: 12px 20px;
  background: #f8f9fa;
  border-top: 1px solid #e9ecef;
  flex-shrink: 0;
  flex-wrap: wrap;
}

.page-btn {
  padding: 6px 18px;
  background: #007bff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  transition: 0.2s;
}

.page-btn:hover:not(:disabled) {
  background: #0056b3;
}

.page-btn:disabled {
  background: #adb5bd;
  cursor: not-allowed;
}

.page-info {
  font-size: 14px;
  color: #495057;
}

.load-all-btn {
  padding: 6px 18px;
  background: #28a745;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  transition: 0.2s;
}

.load-all-btn:hover {
  background: #1e7e34;
}

.empty-state {
  padding: 40px;
  text-align: center;
  color: #6c757d;
  font-size: 16px;
}
</style>