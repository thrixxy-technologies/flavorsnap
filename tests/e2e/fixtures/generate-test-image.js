/**
 * Generate test images for E2E testing
 * Run with: node tests/e2e/fixtures/generate-test-image.js
 */

const fs = require("fs");
const path = require("path");

// Simple function to create a test JPEG image
function generateTestJPEG(filename, width = 224, height = 224) {
  // JPEG header and minimal valid JPEG structure
  const jpegHeader = Buffer.from([
    0xff, 0xd8, 0xff, 0xe0, 0x00, 0x10, 0x4a, 0x46, 0x49, 0x46, 0x00, 0x01,
    0x01, 0x00, 0x00, 0x01, 0x00, 0x01, 0x00, 0x00,
  ]);

  // JPEG footer
  const jpegFooter = Buffer.from([0xff, 0xd9]);

  // Create a simple image data (this is a minimal valid JPEG)
  const imageData = Buffer.alloc(1024);
  imageData.fill(0xff);

  const fullImage = Buffer.concat([jpegHeader, imageData, jpegFooter]);

  const filepath = path.join(__dirname, filename);
  fs.writeFileSync(filepath, fullImage);
  console.log(`Generated test image: ${filepath}`);
}

// Generate test images
generateTestJPEG("test-food.jpg");
generateTestJPEG("test-food-2.jpg");
generateTestJPEG("test-food-large.jpg", 1024, 1024);

console.log("Test images generated successfully!");
