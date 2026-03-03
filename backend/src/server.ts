import express, { Application, Request, Response } from 'express';
import mysql from 'mysql2/promise';
import cors from 'cors';
import helmet from 'helmet';
import dotenv from 'dotenv';
import path from 'path';
import uploadRouter from './routes/upload';
import analyzeRouter from './routes/analyze';

dotenv.config();

const app: Application = express();
const PORT = process.env.PORT || 3001;

app.use(helmet());
app.use(cors());
app.use(express.json());

// Serve static files from uploads directory
app.use('/uploads', express.static(path.join(process.cwd(), 'uploads')));

// API routes
app.use('/api/upload', uploadRouter);
app.use('/api/analyze', analyzeRouter);

// MySQL Connection Pool
export const db = mysql.createPool({
  host: process.env.DB_HOST || '127.0.0.1',
  user: process.env.DB_USER || 'root',
  password: process.env.DB_PASSWORD || '',
  database: process.env.DB_NAME || 'flavorsnap',
  waitForConnections: true,
  connectionLimit: 10,
});

// AUTO-INITIALIZE TABLE (Fix for "command not found")
const initDB = async () => {
  try {
    await db.execute(`
      CREATE TABLE IF NOT EXISTS classification_history (
        id INT AUTO_INCREMENT PRIMARY KEY,
        label VARCHAR(255) NOT NULL,
        confidence DECIMAL(5, 4) NOT NULL,
        image_url TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )
    `);
    console.log('✅ Database table verified/created');
  } catch (err) {
    console.error('❌ Failed to initialize DB:', err);
  }
};

app.get('/health', (req: Request, res: Response) => {
  res.json({ status: 'Backend is running', database: 'Connected' });
});

app.post('/api/history', async (req: Request, res: Response) => {
  const { label, confidence, image_url } = req.body;
  try {
    const [result] = await db.execute(
      'INSERT INTO classification_history (label, confidence, image_url) VALUES (?, ?, ?)',
      [label, confidence, image_url || null]
    );
    res.status(201).json({ success: true, id: (result as any).insertId });
  } catch (error) {
    res.status(500).json({ error: 'Failed to save to database' });
  }
});

app.listen(PORT, async () => {
  await initDB(); // Run the table check on startup
  console.log(`🚀 Express server running on http://localhost:${PORT}`);
});