import React from 'react';

interface FilterControlsProps {
  onApplyFilter: (filter: string) => void;
  onAdjustBrightness: (value: number) => void;
  onAdjustContrast: (value: number) => void;
  onAdjustSaturation: (value: number) => void;
  brightness: number;
  contrast: number;
  saturation: number;
}

const FilterControls: React.FC<FilterControlsProps> = ({
  onApplyFilter,
  onAdjustBrightness,
  onAdjustContrast,
  onAdjustSaturation,
  brightness,
  contrast,
  saturation,
}) => {
  const filters = [
    { name: 'Grayscale', value: 'grayscale' },
    { name: 'Sepia', value: 'sepia' },
    { name: 'Invert', value: 'invert' },
    { name: 'Blur', value: 'blur' },
    { name: 'Sharpen', value: 'sharpen' },
    { name: 'Vintage', value: 'vintage' },
  ];

  return (
    <div className="space-y-6 p-4 bg-white rounded-lg shadow-md">
      <h3 className="text-lg font-semibold mb-4">Filters & Adjustments</h3>

      {/* Quick Filters */}
      <div>
        <label className="text-sm font-medium mb-2 block">Quick Filters</label>
        <div className="grid grid-cols-2 gap-2">
          {filters.map((filter) => (
            <button
              key={filter.value}
              className="px-3 py-2 text-xs border border-gray-300 rounded hover:bg-gray-50 transition-colors"
              onClick={() => onApplyFilter(filter.value)}
            >
              {filter.name}
            </button>
          ))}
        </div>
      </div>

      {/* Brightness */}
      <div>
        <label className="text-sm font-medium mb-2 block">
          Brightness: {brightness}
        </label>
        <input
          type="range"
          value={brightness}
          onChange={(e) => onAdjustBrightness(Number(e.target.value))}
          min={-100}
          max={100}
          step={1}
          className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
        />
      </div>

      {/* Contrast */}
      <div>
        <label className="text-sm font-medium mb-2 block">
          Contrast: {contrast}
        </label>
        <input
          type="range"
          value={contrast}
          onChange={(e) => onAdjustContrast(Number(e.target.value))}
          min={-100}
          max={100}
          step={1}
          className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
        />
      </div>

      {/* Saturation */}
      <div>
        <label className="text-sm font-medium mb-2 block">
          Saturation: {saturation}
        </label>
        <input
          type="range"
          value={saturation}
          onChange={(e) => onAdjustSaturation(Number(e.target.value))}
          min={-100}
          max={100}
          step={1}
          className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
        />
      </div>
    </div>
  );
};

export default FilterControls;