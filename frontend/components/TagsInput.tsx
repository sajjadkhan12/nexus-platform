import React, { useState } from 'react';

interface TagsInputProps {
  tags: Record<string, string>;
  onChange: (tags: Record<string, string>) => void;
  requiredTags?: string[];
  disabled?: boolean;
}

export const TagsInput: React.FC<TagsInputProps> = ({ 
  tags, 
  onChange, 
  requiredTags = ['team', 'owner', 'purpose'],
  disabled = false
}) => {
  const [key, setKey] = useState('');
  const [value, setValue] = useState('');
  const [error, setError] = useState('');
  
  const validateKey = (k: string): boolean => {
    // Key must be lowercase alphanumeric with hyphens
    const keyPattern = /^[a-z0-9-]+$/;
    return keyPattern.test(k);
  };
  
  const addTag = () => {
    setError('');
    
    if (!key.trim()) {
      setError('Tag key cannot be empty');
      return;
    }
    
    if (!value.trim()) {
      setError('Tag value cannot be empty');
      return;
    }
    
    if (!validateKey(key)) {
      setError('Tag key must be lowercase alphanumeric with hyphens only (e.g., "cost-center")');
      return;
    }
    
    if (key in tags) {
      setError(`Tag '${key}' already exists. Remove it first to update.`);
      return;
    }
    
    onChange({ ...tags, [key]: value });
    setKey('');
    setValue('');
  };
  
  const removeTag = (keyToRemove: string) => {
    const newTags = { ...tags };
    delete newTags[keyToRemove];
    onChange(newTags);
  };
  
  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      addTag();
    }
  };
  
  const missingRequired = requiredTags.filter(req => !tags[req]);
  
  return (
    <div className="space-y-3">
      <div className="flex items-start gap-2">
        <div className="flex-1">
          <input
            type="text"
            placeholder="Tag key (e.g., team)"
            value={key}
            onChange={(e) => setKey(e.target.value.toLowerCase())}
            onKeyPress={handleKeyPress}
            disabled={disabled}
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div className="flex-1">
          <input
            type="text"
            placeholder="Tag value"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyPress={handleKeyPress}
            disabled={disabled}
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <button
          onClick={addTag}
          disabled={disabled || !key || !value}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Add Tag
        </button>
      </div>
      
      {error && (
        <div className="text-sm text-red-600 dark:text-red-400">
          {error}
        </div>
      )}
      
      {/* Show required tags that are missing */}
      {missingRequired.length > 0 && (
        <div className="p-3 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg">
          <div className="text-sm font-medium text-yellow-800 dark:text-yellow-200">
            Required tags missing: {missingRequired.join(', ')}
          </div>
          <div className="text-xs text-yellow-700 dark:text-yellow-300 mt-1">
            These tags are required for all deployments
          </div>
        </div>
      )}
      
      {/* Display current tags */}
      {Object.keys(tags).length > 0 && (
        <div className="space-y-2">
          <div className="text-sm font-medium text-gray-700 dark:text-gray-300">
            Tags ({Object.keys(tags).length})
          </div>
          <div className="flex flex-wrap gap-2">
            {Object.entries(tags).map(([k, v]) => {
              const isRequired = requiredTags.includes(k);
              return (
                <span
                  key={k}
                  className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm ${
                    isRequired
                      ? 'bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-200 border border-green-300 dark:border-green-700'
                      : 'bg-gray-100 dark:bg-gray-800 text-gray-800 dark:text-gray-200 border border-gray-300 dark:border-gray-600'
                  }`}
                >
                  <span className="font-medium">{k}:</span>
                  <span>{v}</span>
                  {!disabled && (
                    <button
                      onClick={() => removeTag(k)}
                      className="ml-1 text-gray-500 hover:text-red-600 dark:text-gray-400 dark:hover:text-red-400 transition-colors"
                      title={`Remove tag '${k}'`}
                    >
                      ×
                    </button>
                  )}
                  {isRequired && (
                    <span className="text-xs font-semibold ml-1" title="Required tag">*</span>
                  )}
                </span>
              );
            })}
          </div>
        </div>
      )}
      
      {Object.keys(tags).length === 0 && (
        <div className="text-sm text-gray-500 dark:text-gray-400 italic">
          No tags added yet. Required tags: {requiredTags.join(', ')}
        </div>
      )}
    </div>
  );
};
