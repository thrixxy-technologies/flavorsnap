
const { execSync } = require('child_process');
const path = require('path');

console.log('🚀 Starting Bundle Analysis...');

try {
  // Set environment variable to trigger analyzer in next.config.ts
  process.env.ANALYZE = 'true';
  
  const frontendPath = path.join(__dirname, '../frontend');
  
  console.log('📦 Building frontend...');
  execSync('npm run build', { 
    cwd: frontendPath,
    stdio: 'inherit'
  });

  console.log('✅ Analysis complete! Check the .next/analyze directory for reports.');
} catch (error) {
  console.error('❌ Build failed during analysis:', error.message);
  process.exit(1);
}
