// Frontend Configuration
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000'
export const APP_NAME = import.meta.env.VITE_APP_NAME || 'DuraCapital Financial Analytics'
export const MAX_FILE_SIZE = parseInt(import.meta.env.VITE_MAX_FILE_SIZE) || 50 * 1024 * 1024 // 50MB
export const ALLOWED_FILE_TYPES = (import.meta.env.VITE_ALLOWED_FILE_TYPES || '.csv,.xlsx,.xls,.xlsm,.xlsb,.json,.pdf,.doc,.docx,.docm,.png,.jpg,.jpeg,.gif,.bmp,.tiff,.tif,.txt,.rtf,.xml,.zip,.rar,.7z,.tar,.gz,.odt,.ods,.odp,.ppt,.pptx,.pptm').split(',')
export const RATE_LIMIT_MESSAGE = import.meta.env.VITE_RATE_LIMIT_MESSAGE || 'Too many requests. Please try again later.'
