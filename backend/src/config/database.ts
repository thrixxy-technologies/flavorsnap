import mysql from 'mysql2/promise';
import { createPool } from 'mysql2/promise';

// Database connection configuration
const dbConfig = {
  host: process.env.DB_HOST || 'localhost',
  port: parseInt(process.env.DB_PORT || '3306'),
  user: process.env.DB_USER || 'root',
  password: process.env.DB_PASSWORD || '',
  database: process.env.DB_NAME || 'flavorsnap',
  waitForConnections: true,
  connectionLimit: parseInt(process.env.DB_CONNECTION_LIMIT || '10'),
  queueLimit: parseInt(process.env.DB_QUEUE_LIMIT || '0'),
  acquireTimeout: parseInt(process.env.DB_ACQUIRE_TIMEOUT || '60000'),
  timeout: parseInt(process.env.DB_TIMEOUT || '60000'),
  reconnect: true,
  charset: 'utf8mb4'
};

// Create connection pool
const pool = createPool(dbConfig);

// Test database connection
export async function testConnection(): Promise<boolean> {
  try {
    const connection = await pool.getConnection();
    await connection.ping();
    connection.release();
    console.log('✅ Database connection successful');
    return true;
  } catch (error) {
    console.error('❌ Database connection failed:', error);
    return false;
  }
}

// Connect to database
export async function connectDatabase(): Promise<void> {
  const isConnected = await testConnection();
  if (!isConnected) {
    throw new Error('Failed to connect to database');
  }
}

// Get connection from pool
export function getConnection(): Promise<mysql.Connection> {
  return pool.getConnection();
}

// Execute query with connection
export async function executeQuery<T = any>(
  query: string, 
  params?: any[]
): Promise<T[]> {
  const connection = await getConnection();
  try {
    const [rows] = await connection.execute(query, params);
    return rows as T[];
  } finally {
    connection.release();
  }
}

// Execute single query (for INSERT, UPDATE, DELETE)
export async function executeNonQuery(
  query: string, 
  params?: any[]
): Promise<mysql.ResultSetHeader> {
  const connection = await getConnection();
  try {
    const [result] = await connection.execute(query, params);
    return result as mysql.ResultSetHeader;
  } finally {
    connection.release();
  }
}

// Transaction helper
export async function executeTransaction<T>(
  queries: Array<{ query: string; params?: any[] }>
): Promise<T[]> {
  const connection = await getConnection();
  try {
    await connection.beginTransaction();
    const results: T[] = [];
    
    for (const { query, params } of queries) {
      const [result] = await connection.execute(query, params);
      results.push(result as T);
    }
    
    await connection.commit();
    return results;
  } catch (error) {
    await connection.rollback();
    throw error;
  } finally {
    connection.release();
  }
}

// Close all connections
export async function closeDatabase(): Promise<void> {
  await pool.end();
  console.log('📴 Database connections closed');
}

export default pool;
