import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Search, Filter, Grid, List, ExternalLink, ShoppingBag, Trophy, Utensils, Star } from 'lucide-react';
import Image from 'next/image';

interface NFTMetadata {
  name: string;
  description: string;
  image: string;
  external_url?: string;
  attributes?: Array<{
    trait_type: string;
    value: string;
  }>;
  food_type?: string;
  ingredients?: string[];
  nutrition_info?: Record<string, any>;
  recipe_steps?: string[];
  contributor?: string;
  creation_date?: string;
  rarity?: string;
  flavor_profile?: string[];
}

interface NFTRecord {
  id: number;
  token_id?: number;
  nft_type: 'food_item' | 'recipe' | 'achievement' | 'contributor_badge';
  status: 'pending' | 'minting' | 'minted' | 'listed' | 'sold' | 'error';
  metadata_hash: string;
  image_hash: string;
  owner_address?: string;
  transaction_hash?: string;
  block_number?: number;
  minted_at?: string;
  listed_price?: number;
  created_at: string;
  updated_at: string;
}

interface NFTGalleryProps {
  userAddress?: string;
  onNFTSelect?: (nft: NFTRecord & { metadata: NFTMetadata }) => void;
  showMintButton?: boolean;
}

const NFTGallery: React.FC<NFTGalleryProps> = ({ 
  userAddress, 
  onNFTSelect, 
  showMintButton = true 
}) => {
  const [nfts, setNfts] = useState<(NFTRecord & { metadata: NFTMetadata })[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterType, setFilterType] = useState<string>('all');
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [sortBy, setSortBy] = useState<string>('created_at');
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [selectedNFT, setSelectedNFT] = useState<NFTRecord & { metadata: NFTMetadata } | null>(null);
  const [showDetails, setShowDetails] = useState(false);

  useEffect(() => {
    fetchNFTs();
  }, [userAddress, filterType, filterStatus, sortBy]);

  const fetchNFTs = async () => {
    try {
      setLoading(true);
      const endpoint = userAddress 
        ? `/api/nft/owner/${userAddress}`
        : '/api/nft/all';
      
      const response = await fetch(endpoint);
      const data = await response.json();
      
      let filteredNFTs = data.nfts || [];
      
      // Apply filters
      if (filterType !== 'all') {
        filteredNFTs = filteredNFTs.filter((nft: any) => nft.nft_type === filterType);
      }
      
      if (filterStatus !== 'all') {
        filteredNFTs = filteredNFTs.filter((nft: any) => nft.status === filterStatus);
      }
      
      if (searchTerm) {
        filteredNFTs = filteredNFTs.filter((nft: any) => 
          nft.metadata?.name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
          nft.metadata?.description?.toLowerCase().includes(searchTerm.toLowerCase())
        );
      }
      
      // Sort
      filteredNFTs.sort((a: any, b: any) => {
        switch (sortBy) {
          case 'name':
            return (a.metadata?.name || '').localeCompare(b.metadata?.name || '');
          case 'created_at':
            return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
          case 'listed_price':
            return (b.listed_price || 0) - (a.listed_price || 0);
          default:
            return 0;
        }
      });
      
      setNfts(filteredNFTs);
    } catch (error) {
      console.error('Failed to fetch NFTs:', error);
    } finally {
      setLoading(false);
    }
  };

  const getRarityColor = (rarity?: string) => {
    switch (rarity) {
      case 'legendary': return 'bg-yellow-500';
      case 'epic': return 'bg-purple-500';
      case 'rare': return 'bg-blue-500';
      case 'uncommon': return 'bg-green-500';
      case 'common': return 'bg-gray-500';
      default: return 'bg-gray-400';
    }
  };

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'food_item': return <Utensils className="w-4 h-4" />;
      case 'recipe': return <Star className="w-4 h-4" />;
      case 'achievement': return <Trophy className="w-4 h-4" />;
      case 'contributor_badge': return <ShoppingBag className="w-4 h-4" />;
      default: return <Grid className="w-4 h-4" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'minted': return 'bg-green-100 text-green-800';
      case 'listed': return 'bg-blue-100 text-blue-800';
      case 'sold': return 'bg-purple-100 text-purple-800';
      case 'pending': return 'bg-yellow-100 text-yellow-800';
      case 'minting': return 'bg-orange-100 text-orange-800';
      case 'error': return 'bg-red-100 text-red-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const NFTCard: React.FC<{ nft: NFTRecord & { metadata: NFTMetadata } }> = ({ nft }) => (
    <Card className="overflow-hidden hover:shadow-lg transition-shadow cursor-pointer"
          onClick={() => {
            setSelectedNFT(nft);
            setShowDetails(true);
            onNFTSelect?.(nft);
          }}>
      <div className="relative aspect-square">
        <Image
          src={nft.metadata.image}
          alt={nft.metadata.name}
          fill
          className="object-cover"
        />
        <div className="absolute top-2 right-2">
          <Badge className={getRarityColor(nft.metadata.rarity)}>
            {nft.metadata.rarity || 'common'}
          </Badge>
        </div>
        <div className="absolute top-2 left-2">
          <Badge variant="secondary" className="flex items-center gap-1">
            {getTypeIcon(nft.nft_type)}
            {nft.nft_type.replace('_', ' ')}
          </Badge>
        </div>
      </div>
      
      <CardContent className="p-4">
        <div className="flex justify-between items-start mb-2">
          <h3 className="font-semibold text-lg truncate">{nft.metadata.name}</h3>
          <Badge className={getStatusColor(nft.status)}>
            {nft.status}
          </Badge>
        </div>
        
        <p className="text-sm text-gray-600 line-clamp-2 mb-3">
          {nft.metadata.description}
        </p>
        
        {nft.listed_price && (
          <div className="flex justify-between items-center">
            <span className="text-lg font-bold text-blue-600">
              {nft.listed_price} ETH
            </span>
            <Button size="sm" variant="outline">
              <ExternalLink className="w-4 h-4 mr-1" />
              View
            </Button>
          </div>
        )}
        
        {nft.metadata.attributes && (
          <div className="flex flex-wrap gap-1 mt-2">
            {nft.metadata.attributes.slice(0, 3).map((attr, index) => (
              <Badge key={index} variant="outline" className="text-xs">
                {attr.trait_type}: {attr.value}
              </Badge>
            ))}
            {nft.metadata.attributes.length > 3 && (
              <Badge variant="outline" className="text-xs">
                +{nft.metadata.attributes.length - 3} more
              </Badge>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );

  const NFTListItem: React.FC<{ nft: NFTRecord & { metadata: NFTMetadata } }> = ({ nft }) => (
    <Card className="p-4 hover:shadow-md transition-shadow cursor-pointer"
          onClick={() => {
            setSelectedNFT(nft);
            setShowDetails(true);
            onNFTSelect?.(nft);
          }}>
      <div className="flex gap-4">
        <div className="relative w-20 h-20 flex-shrink-0">
          <Image
            src={nft.metadata.image}
            alt={nft.metadata.name}
            fill
            className="object-cover rounded"
          />
        </div>
        
        <div className="flex-1 min-w-0">
          <div className="flex justify-between items-start mb-2">
            <h3 className="font-semibold text-lg truncate">{nft.metadata.name}</h3>
            <div className="flex gap-2">
              <Badge className={getRarityColor(nft.metadata.rarity)}>
                {nft.metadata.rarity || 'common'}
              </Badge>
              <Badge className={getStatusColor(nft.status)}>
                {nft.status}
              </Badge>
            </div>
          </div>
          
          <p className="text-sm text-gray-600 line-clamp-2 mb-2">
            {nft.metadata.description}
          </p>
          
          <div className="flex items-center gap-4 text-sm text-gray-500">
            <span className="flex items-center gap-1">
              {getTypeIcon(nft.nft_type)}
              {nft.nft_type.replace('_', ' ')}
            </span>
            {nft.token_id && (
              <span>Token ID: {nft.token_id}</span>
            )}
            {nft.listed_price && (
              <span className="font-bold text-blue-600">
                {nft.listed_price} ETH
              </span>
            )}
          </div>
        </div>
      </div>
    </Card>
  );

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-[400px]">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold">NFT Gallery</h2>
        {showMintButton && (
          <Button>
            <ShoppingBag className="w-4 h-4 mr-2" />
            Mint New NFT
          </Button>
        )}
      </div>

      {/* Filters and Search */}
      <Card>
        <CardContent className="p-4">
          <div className="flex flex-wrap gap-4 items-center">
            <div className="flex-1 min-w-[200px]">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
                <Input
                  placeholder="Search NFTs..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>
            
            <Select value={filterType} onValueChange={setFilterType}>
              <SelectTrigger className="w-[150px]">
                <SelectValue placeholder="Type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Types</SelectItem>
                <SelectItem value="food_item">Food Items</SelectItem>
                <SelectItem value="recipe">Recipes</SelectItem>
                <SelectItem value="achievement">Achievements</SelectItem>
                <SelectItem value="contributor_badge">Badges</SelectItem>
              </SelectContent>
            </Select>
            
            <Select value={filterStatus} onValueChange={setFilterStatus}>
              <SelectTrigger className="w-[150px]">
                <SelectValue placeholder="Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Status</SelectItem>
                <SelectItem value="minted">Minted</SelectItem>
                <SelectItem value="listed">Listed</SelectItem>
                <SelectItem value="sold">Sold</SelectItem>
                <SelectItem value="pending">Pending</SelectItem>
              </SelectContent>
            </Select>
            
            <Select value={sortBy} onValueChange={setSortBy}>
              <SelectTrigger className="w-[150px]">
                <SelectValue placeholder="Sort by" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="created_at">Created</SelectItem>
                <SelectItem value="name">Name</SelectItem>
                <SelectItem value="listed_price">Price</SelectItem>
              </SelectContent>
            </Select>
            
            <div className="flex gap-2">
              <Button
                variant={viewMode === 'grid' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setViewMode('grid')}
              >
                <Grid className="w-4 h-4" />
              </Button>
              <Button
                variant={viewMode === 'list' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setViewMode('list')}
              >
                <List className="w-4 h-4" />
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* NFT Grid/List */}
      {nfts.length === 0 ? (
        <Card>
          <CardContent className="p-8 text-center">
            <div className="text-gray-500">
              <Grid className="w-12 h-12 mx-auto mb-4 opacity-50" />
              <p className="text-lg">No NFTs found</p>
              <p className="text-sm">Try adjusting your filters or mint your first NFT</p>
            </div>
          </CardContent>
        </Card>
      ) : (
        <div className={viewMode === 'grid' 
          ? 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6'
          : 'space-y-4'
        }>
          {nfts.map((nft) => 
            viewMode === 'grid' 
              ? <NFTCard key={nft.id} nft={nft} />
              : <NFTListItem key={nft.id} nft={nft} />
          )}
        </div>
      )}

      {/* NFT Details Dialog */}
      <Dialog open={showDetails} onOpenChange={setShowDetails}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
          {selectedNFT && (
            <>
              <DialogHeader>
                <DialogTitle className="flex items-center gap-2">
                  {getTypeIcon(selectedNFT.nft_type)}
                  {selectedNFT.metadata.name}
                </DialogTitle>
              </DialogHeader>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <div className="relative aspect-square rounded-lg overflow-hidden">
                    <Image
                      src={selectedNFT.metadata.image}
                      alt={selectedNFT.metadata.name}
                      fill
                      className="object-cover"
                    />
                  </div>
                </div>
                
                <div className="space-y-4">
                  <div>
                    <h3 className="text-xl font-semibold mb-2">{selectedNFT.metadata.name}</h3>
                    <p className="text-gray-600">{selectedNFT.metadata.description}</p>
                  </div>
                  
                  <div className="flex gap-2">
                    <Badge className={getRarityColor(selectedNFT.metadata.rarity)}>
                      {selectedNFT.metadata.rarity || 'common'}
                    </Badge>
                    <Badge className={getStatusColor(selectedNFT.status)}>
                      {selectedNFT.status}
                    </Badge>
                    <Badge variant="secondary">
                      {selectedNFT.nft_type.replace('_', ' ')}
                    </Badge>
                  </div>
                  
                  {selectedNFT.listed_price && (
                    <div className="text-2xl font-bold text-blue-600">
                      {selectedNFT.listed_price} ETH
                    </div>
                  )}
                  
                  {selectedNFT.metadata.food_type && (
                    <div>
                      <h4 className="font-semibold mb-2">Food Type</h4>
                      <p>{selectedNFT.metadata.food_type}</p>
                    </div>
                  )}
                  
                  {selectedNFT.metadata.ingredients && (
                    <div>
                      <h4 className="font-semibold mb-2">Ingredients</h4>
                      <div className="flex flex-wrap gap-2">
                        {selectedNFT.metadata.ingredients.map((ingredient, index) => (
                          <Badge key={index} variant="outline">
                            {ingredient}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  )}
                  
                  {selectedNFT.metadata.flavor_profile && (
                    <div>
                      <h4 className="font-semibold mb-2">Flavor Profile</h4>
                      <div className="flex flex-wrap gap-2">
                        {selectedNFT.metadata.flavor_profile.map((flavor, index) => (
                          <Badge key={index} variant="secondary">
                            {flavor}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  )}
                  
                  {selectedNFT.metadata.attributes && (
                    <div>
                      <h4 className="font-semibold mb-2">Attributes</h4>
                      <div className="space-y-2">
                        {selectedNFT.metadata.attributes.map((attr, index) => (
                          <div key={index} className="flex justify-between">
                            <span className="font-medium">{attr.trait_type}:</span>
                            <span>{attr.value}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  
                  <div className="pt-4 border-t">
                    <div className="grid grid-cols-2 gap-4 text-sm text-gray-500">
                      <div>
                        <span className="font-medium">Token ID:</span>
                        <span className="ml-2">{selectedNFT.token_id || 'N/A'}</span>
                      </div>
                      <div>
                        <span className="font-medium">Created:</span>
                        <span className="ml-2">
                          {new Date(selectedNFT.created_at).toLocaleDateString()}
                        </span>
                      </div>
                      {selectedNFT.owner_address && (
                        <div className="col-span-2">
                          <span className="font-medium">Owner:</span>
                          <span className="ml-2 font-mono text-xs">
                            {selectedNFT.owner_address.slice(0, 6)}...
                            {selectedNFT.owner_address.slice(-4)}
                          </span>
                        </div>
                      )}
                    </div>
                  </div>
                  
                  <div className="flex gap-2 pt-4">
                    <Button className="flex-1">
                      <ShoppingBag className="w-4 h-4 mr-2" />
                      Buy Now
                    </Button>
                    <Button variant="outline" className="flex-1">
                      <ExternalLink className="w-4 h-4 mr-2" />
                      View on Marketplace
                    </Button>
                  </div>
                </div>
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default NFTGallery;
