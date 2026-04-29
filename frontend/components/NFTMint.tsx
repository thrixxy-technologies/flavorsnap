import React, { useState, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Label } from '@/components/ui/label';
import { Progress } from '@/components/ui/progress';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Upload, Image as ImageIcon, Plus, X, CheckCircle, AlertCircle, Loader2 } from 'lucide-react';
import Image from 'next/image';

interface NFTMintProps {
  userAddress?: string;
  onMintSuccess?: (result: any) => void;
  onMintError?: (error: string) => void;
}

interface FormData {
  name: string;
  description: string;
  food_type?: string;
  ingredients: string[];
  recipe_steps: string[];
  flavor_profile: string[];
  nutrition_info: Record<string, any>;
  rarity: string;
  achievement_type?: string;
  contributor?: string;
}

const NFTMint: React.FC<NFTMintProps> = ({ 
  userAddress, 
  onMintSuccess, 
  onMintError 
}) => {
  const [activeTab, setActiveTab] = useState('food_item');
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string>('');
  const [minting, setMinting] = useState(false);
  const [mintProgress, setMintProgress] = useState(0);
  const [mintStatus, setMintStatus] = useState<'idle' | 'uploading' | 'minting' | 'success' | 'error'>('idle');
  const [error, setError] = useState<string>('');
  const [success, setSuccess] = useState<string>('');
  
  const [formData, setFormData] = useState<FormData>({
    name: '',
    description: '',
    food_type: '',
    ingredients: [''],
    recipe_steps: [''],
    flavor_profile: [],
    nutrition_info: {},
    rarity: 'common',
    achievement_type: '',
    contributor: ''
  });

  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleImageUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      // Validate file size (10MB limit)
      if (file.size > 10 * 1024 * 1024) {
        setError('Image file must be less than 10MB');
        return;
      }

      // Validate file type
      if (!file.type.startsWith('image/')) {
        setError('Please upload an image file');
        return;
      }

      setImageFile(file);
      
      // Create preview
      const reader = new FileReader();
      reader.onload = (e) => {
        setImagePreview(e.target?.result as string);
      };
      reader.readAsDataURL(file);
      
      setError('');
    }
  };

  const updateFormData = (field: keyof FormData, value: any) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const addArrayItem = (field: 'ingredients' | 'recipe_steps' | 'flavor_profile') => {
    setFormData(prev => ({
      ...prev,
      [field]: [...prev[field], '']
    }));
  };

  const removeArrayItem = (field: 'ingredients' | 'recipe_steps' | 'flavor_profile', index: number) => {
    setFormData(prev => ({
      ...prev,
      [field]: prev[field].filter((_, i) => i !== index)
    }));
  };

  const updateArrayItem = (field: 'ingredients' | 'recipe_steps' | 'flavor_profile', index: number, value: string) => {
    setFormData(prev => ({
      ...prev,
      [field]: prev[field].map((item, i) => i === index ? value : item)
    }));
  };

  const updateNutritionInfo = (nutrient: string, value: string) => {
    setFormData(prev => ({
      ...prev,
      nutrition_info: {
        ...prev.nutrition_info,
        [nutrient]: value
      }
    }));
  };

  const validateForm = (): boolean => {
    if (!formData.name.trim()) {
      setError('Name is required');
      return false;
    }

    if (!formData.description.trim()) {
      setError('Description is required');
      return false;
    }

    if (!imageFile) {
      setError('Image is required');
      return false;
    }

    if (activeTab === 'food_item') {
      if (!formData.food_type) {
        setError('Food type is required for food items');
        return false;
      }
    }

    if (activeTab === 'recipe') {
      const validIngredients = formData.ingredients.filter(ing => ing.trim());
      const validSteps = formData.recipe_steps.filter(step => step.trim());
      
      if (validIngredients.length === 0) {
        setError('At least one ingredient is required for recipes');
        return false;
      }

      if (validSteps.length === 0) {
        setError('At least one recipe step is required');
        return false;
      }
    }

    return true;
  };

  const mintNFT = async () => {
    if (!validateForm()) {
      return;
    }

    if (!userAddress) {
      setError('Please connect your wallet first');
      return;
    }

    try {
      setMinting(true);
      setMintStatus('uploading');
      setMintProgress(0);
      setError('');
      setSuccess('');

      // Convert image to bytes
      const imageBytes = await imageFile.arrayBuffer();
      const imageData = new Uint8Array(imageBytes);

      // Prepare metadata
      const metadata = {
        name: formData.name,
        description: formData.description,
        food_type: activeTab === 'food_item' ? formData.food_type : undefined,
        ingredients: activeTab === 'recipe' ? formData.ingredients.filter(ing => ing.trim()) : undefined,
        recipe_steps: activeTab === 'recipe' ? formData.recipe_steps.filter(step => step.trim()) : undefined,
        flavor_profile: formData.flavor_profile.length > 0 ? formData.flavor_profile : undefined,
        nutrition_info: Object.keys(formData.nutrition_info).length > 0 ? formData.nutrition_info : undefined,
        rarity: formData.rarity,
        achievement_type: activeTab === 'achievement' ? formData.achievement_type : undefined,
        contributor: formData.contributor || undefined,
        creation_date: new Date().toISOString(),
        attributes: [
          ...(formData.flavor_profile.map(flavor => ({ trait_type: 'Flavor', value: flavor }))),
          { trait_type: 'Rarity', value: formData.rarity },
          ...(activeTab === 'achievement' ? [{ trait_type: 'Achievement Type', value: formData.achievement_type }] : [])
        ]
      };

      setMintProgress(25);

      // Call minting API
      setMintStatus('minting');
      const endpoint = `/api/nft/mint/${activeTab}`;
      
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          metadata,
          image_data: Array.from(imageData),
          owner_address: userAddress
        })
      });

      setMintProgress(75);

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Minting failed');
      }

      const result = await response.json();
      
      setMintProgress(100);
      setMintStatus('success');
      setSuccess(`NFT "${formData.name}" minted successfully! Token ID: ${result.token_id}`);
      
      // Reset form
      resetForm();
      
      // Call success callback
      onMintSuccess?.(result);

    } catch (error: any) {
      setMintStatus('error');
      const errorMessage = error.message || 'Failed to mint NFT';
      setError(errorMessage);
      onMintError?.(errorMessage);
    } finally {
      setMinting(false);
    }
  };

  const resetForm = () => {
    setFormData({
      name: '',
      description: '',
      food_type: '',
      ingredients: [''],
      recipe_steps: [''],
      flavor_profile: [],
      nutrition_info: {},
      rarity: 'common',
      achievement_type: '',
      contributor: ''
    });
    setImageFile(null);
    setImagePreview('');
    setMintStatus('idle');
    setMintProgress(0);
  };

  const FoodItemForm = () => (
    <div className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <Label htmlFor="food_type">Food Type</Label>
          <Select value={formData.food_type} onValueChange={(value) => updateFormData('food_type', value)}>
            <SelectTrigger>
              <SelectValue placeholder="Select food type" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="pizza">Pizza</SelectItem>
              <SelectItem value="burger">Burger</SelectItem>
              <SelectItem value="salad">Salad</SelectItem>
              <SelectItem value="pasta">Pasta</SelectItem>
              <SelectItem value="dessert">Dessert</SelectItem>
              <SelectItem value="beverage">Beverage</SelectItem>
              <SelectItem value="snack">Snack</SelectItem>
              <SelectItem value="soup">Soup</SelectItem>
              <SelectItem value="sandwich">Sandwich</SelectItem>
              <SelectItem value="other">Other</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div>
          <Label htmlFor="rarity">Rarity</Label>
          <Select value={formData.rarity} onValueChange={(value) => updateFormData('rarity', value)}>
            <SelectTrigger>
              <SelectValue placeholder="Select rarity" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="common">Common</SelectItem>
              <SelectItem value="uncommon">Uncommon</SelectItem>
              <SelectItem value="rare">Rare</SelectItem>
              <SelectItem value="epic">Epic</SelectItem>
              <SelectItem value="legendary">Legendary</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      <div>
        <Label>Flavor Profile</Label>
        <div className="space-y-2">
          {formData.flavor_profile.map((flavor, index) => (
            <div key={index} className="flex gap-2">
              <Input
                value={flavor}
                onChange={(e) => updateArrayItem('flavor_profile', index, e.target.value)}
                placeholder="Enter flavor (e.g., sweet, spicy, savory)"
              />
              {formData.flavor_profile.length > 1 && (
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => removeArrayItem('flavor_profile', index)}
                >
                  <X className="w-4 h-4" />
                </Button>
              )}
            </div>
          ))}
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => addArrayItem('flavor_profile')}
          >
            <Plus className="w-4 h-4 mr-1" />
            Add Flavor
          </Button>
        </div>
      </div>

      <div>
        <Label>Nutrition Information (Optional)</Label>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
          <Input
            placeholder="Calories"
            value={formData.nutrition_info.calories || ''}
            onChange={(e) => updateNutritionInfo('calories', e.target.value)}
          />
          <Input
            placeholder="Protein (g)"
            value={formData.nutrition_info.protein || ''}
            onChange={(e) => updateNutritionInfo('protein', e.target.value)}
          />
          <Input
            placeholder="Carbs (g)"
            value={formData.nutrition_info.carbs || ''}
            onChange={(e) => updateNutritionInfo('carbs', e.target.value)}
          />
          <Input
            placeholder="Fat (g)"
            value={formData.nutrition_info.fat || ''}
            onChange={(e) => updateNutritionInfo('fat', e.target.value)}
          />
        </div>
      </div>
    </div>
  );

  const RecipeForm = () => (
    <div className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <Label htmlFor="rarity">Rarity</Label>
          <Select value={formData.rarity} onValueChange={(value) => updateFormData('rarity', value)}>
            <SelectTrigger>
              <SelectValue placeholder="Select rarity" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="common">Common</SelectItem>
              <SelectItem value="uncommon">Uncommon</SelectItem>
              <SelectItem value="rare">Rare</SelectItem>
              <SelectItem value="epic">Epic</SelectItem>
              <SelectItem value="legendary">Legendary</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div>
          <Label htmlFor="contributor">Contributor (Optional)</Label>
          <Input
            id="contributor"
            value={formData.contributor}
            onChange={(e) => updateFormData('contributor', e.target.value)}
            placeholder="Recipe contributor name"
          />
        </div>
      </div>

      <div>
        <Label>Ingredients</Label>
        <div className="space-y-2">
          {formData.ingredients.map((ingredient, index) => (
            <div key={index} className="flex gap-2">
              <Input
                value={ingredient}
                onChange={(e) => updateArrayItem('ingredients', index, e.target.value)}
                placeholder="Enter ingredient"
              />
              {formData.ingredients.length > 1 && (
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => removeArrayItem('ingredients', index)}
                >
                  <X className="w-4 h-4" />
                </Button>
              )}
            </div>
          ))}
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => addArrayItem('ingredients')}
          >
            <Plus className="w-4 h-4 mr-1" />
            Add Ingredient
          </Button>
        </div>
      </div>

      <div>
        <Label>Recipe Steps</Label>
        <div className="space-y-2">
          {formData.recipe_steps.map((step, index) => (
            <div key={index} className="flex gap-2">
              <div className="flex items-center justify-center w-8 h-8 rounded-full bg-gray-100 text-sm font-medium">
                {index + 1}
              </div>
              <Textarea
                value={step}
                onChange={(e) => updateArrayItem('recipe_steps', index, e.target.value)}
                placeholder="Enter recipe step"
                rows={2}
              />
              {formData.recipe_steps.length > 1 && (
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => removeArrayItem('recipe_steps', index)}
                >
                  <X className="w-4 h-4" />
                </Button>
              )}
            </div>
          ))}
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => addArrayItem('recipe_steps')}
          >
            <Plus className="w-4 h-4 mr-1" />
            Add Step
          </Button>
        </div>
      </div>
    </div>
  );

  const AchievementForm = () => (
    <div className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <Label htmlFor="achievement_type">Achievement Type</Label>
          <Select value={formData.achievement_type} onValueChange={(value) => updateFormData('achievement_type', value)}>
            <SelectTrigger>
              <SelectValue placeholder="Select achievement type" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="first_recipe">First Recipe Created</SelectItem>
              <SelectItem value="recipe_master">Recipe Master (100+ recipes)</SelectItem>
              <SelectItem value="food_critic">Food Critic</SelectItem>
              <SelectItem value="community_helper">Community Helper</SelectItem>
              <SelectItem value="early_adopter">Early Adopter</SelectItem>
              <SelectItem value="contributor">Top Contributor</SelectItem>
              <SelectItem value="innovation">Innovation Award</SelectItem>
              <SelectItem value="milestone">Milestone Achievement</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div>
          <Label htmlFor="rarity">Rarity</Label>
          <Select value={formData.rarity} onValueChange={(value) => updateFormData('rarity', value)}>
            <SelectTrigger>
              <SelectValue placeholder="Select rarity" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="common">Common</SelectItem>
              <SelectItem value="uncommon">Uncommon</SelectItem>
              <SelectItem value="rare">Rare</SelectItem>
              <SelectItem value="epic">Epic</SelectItem>
              <SelectItem value="legendary">Legendary</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      <div>
        <Label htmlFor="contributor">Recipient</Label>
        <Input
          id="contributor"
          value={formData.contributor}
          onChange={(e) => updateFormData('contributor', e.target.value)}
          placeholder="Achievement recipient name or address"
        />
      </div>
    </div>
  );

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Mint New NFT</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Image Upload */}
          <div>
            <Label>Upload Image</Label>
            <div className="mt-2">
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                onChange={handleImageUpload}
                className="hidden"
              />
              
              {imagePreview ? (
                <div className="relative">
                  <div className="relative aspect-square max-w-sm mx-auto rounded-lg overflow-hidden">
                    <Image
                      src={imagePreview}
                      alt="Preview"
                      fill
                      className="object-cover"
                    />
                  </div>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    className="absolute top-2 right-2"
                    onClick={() => {
                      setImageFile(null);
                      setImagePreview('');
                    }}
                  >
                    <X className="w-4 h-4" />
                  </Button>
                </div>
              ) : (
                <div
                  className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center cursor-pointer hover:border-gray-400"
                  onClick={() => fileInputRef.current?.click()}
                >
                  <ImageIcon className="w-12 h-12 mx-auto mb-4 text-gray-400" />
                  <p className="text-gray-600">Click to upload image</p>
                  <p className="text-sm text-gray-500">PNG, JPG, GIF up to 10MB</p>
                </div>
              )}
            </div>
          </div>

          {/* Basic Information */}
          <div className="space-y-4">
            <div>
              <Label htmlFor="name">Name *</Label>
              <Input
                id="name"
                value={formData.name}
                onChange={(e) => updateFormData('name', e.target.value)}
                placeholder="Enter NFT name"
                maxLength={100}
              />
            </div>

            <div>
              <Label htmlFor="description">Description *</Label>
              <Textarea
                id="description"
                value={formData.description}
                onChange={(e) => updateFormData('description', e.target.value)}
                placeholder="Enter NFT description"
                rows={3}
                maxLength={1000}
              />
            </div>
          </div>

          {/* Type-specific forms */}
          <Tabs value={activeTab} onValueChange={setActiveTab}>
            <TabsList className="grid w-full grid-cols-3">
              <TabsTrigger value="food_item">Food Item</TabsTrigger>
              <TabsTrigger value="recipe">Recipe</TabsTrigger>
              <TabsTrigger value="achievement">Achievement</TabsTrigger>
            </TabsList>

            <TabsContent value="food_item" className="space-y-4">
              <FoodItemForm />
            </TabsContent>

            <TabsContent value="recipe" className="space-y-4">
              <RecipeForm />
            </TabsContent>

            <TabsContent value="achievement" className="space-y-4">
              <AchievementForm />
            </TabsContent>
          </Tabs>

          {/* Status Messages */}
          {error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {success && (
            <Alert>
              <CheckCircle className="h-4 w-4" />
              <AlertDescription>{success}</AlertDescription>
            </Alert>
          )}

          {/* Minting Progress */}
          {minting && (
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                {mintStatus === 'uploading' && <><Loader2 className="w-4 h-4 animate-spin" /> Uploading to IPFS...</>}
                {mintStatus === 'minting' && <><Loader2 className="w-4 h-4 animate-spin" /> Minting on blockchain...</>}
                {mintStatus === 'success' && <><CheckCircle className="w-4 h-4 text-green-600" /> NFT Minted Successfully!</>}
                {mintStatus === 'error' && <><AlertCircle className="w-4 h-4 text-red-600" /> Minting Failed</>}
              </div>
              <Progress value={mintProgress} className="w-full" />
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex gap-2">
            <Button
              onClick={mintNFT}
              disabled={minting || !userAddress}
              className="flex-1"
            >
              {minting ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Minting...
                </>
              ) : (
                'Mint NFT'
              )}
            </Button>
            
            <Button
              variant="outline"
              onClick={resetForm}
              disabled={minting}
            >
              Reset
            </Button>
          </div>

          {!userAddress && (
            <Alert>
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                Please connect your wallet to mint NFTs
              </AlertDescription>
            </Alert>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default NFTMint;
