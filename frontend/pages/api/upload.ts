import type { NextApiRequest, NextApiResponse } from "next";
import FormData from 'form-data';

type ClassificationResult = {
  label?: string;
  food?: string;
  confidence: number;
  calories?: number;
};

type Data = ClassificationResult | { error: string };

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse<Data>,
) {
  // Only allow POST requests
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    // Check if file is present
    if (!req.body || !req.body.get) {
      return res.status(400).json({ error: 'No file uploaded' });
    }

    const file = req.body.get('file');
    
    if (!file) {
      return res.status(400).json({ error: 'No file in upload' });
    }

    // Check file type
    if (!file.type || !file.type.startsWith('image/')) {
      return res.status(400).json({ error: 'Invalid file type. Please upload an image.' });
    }

    // Check file size (max 10MB)
    const maxSize = 10 * 1024 * 1024; // 10MB in bytes
    if (file.size > maxSize) {
      return res.status(400).json({ error: 'File too large. Maximum size is 10MB.' });
    }

    // Simulate processing delay
    await new Promise(resolve => setTimeout(resolve, 1000 + Math.random() * 2000));

    // Simulate random errors for testing (20% chance)
    if (Math.random() < 0.2) {
      return res.status(500).json({ error: 'Classification service temporarily unavailable. Please try again.' });
    }

    // Mock classification result
    const foods = [
      { name: "Pizza Margherita", calories: 285 },
      { name: "Caesar Salad", calories: 180 },
      { name: "Grilled Chicken", calories: 231 },
      { name: "Spaghetti Carbonara", calories: 584 },
      { name: "Sushi Roll", calories: 200 },
      { name: "Beef Burger", calories: 540 },
      { name: "Vegetable Stir Fry", calories: 150 },
      { name: "Chocolate Cake", calories: 350 },
      { name: "Greek Yogurt", calories: 100 },
      { name: "Avocado Toast", calories: 320 }
    ];
    
    const randomFood = foods[Math.floor(Math.random() * foods.length)];
    
    const result: ClassificationResult = {
      food: randomFood.name,
      confidence: Math.random() * 0.3 + 0.7, // 0.7 to 1.0
      calories: randomFood.calories,
    };

    res.status(200).json(result);
  } catch (error: any) {
    console.error('Upload error:', error);
    res.status(500).json({ 
      error: error.message || 'Internal server error during classification' 
    });
  }
}
