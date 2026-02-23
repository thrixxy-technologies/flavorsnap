import { NextRequest, NextResponse } from "next/server";
import { writeFile, mkdir } from "fs/promises";
import { join } from "path";
import { logger, withLogging } from "@/lib/logger";

async function predictHandler(request: NextRequest) {
  try {
    const formData = await request.formData();
    const file = formData.get("image") as File | null;

    // 1. Validation
    if (!file) {
      logger.warning("No image provided in request", { hasFormData: !!formData });
      return NextResponse.json(
        { error: "No image provided" },
        { status: 400 }
      );
    }

    const validTypes = ["image/jpeg", "image/png", "image/webp"];
    if (!validTypes.includes(file.type)) {
      logger.warning("Invalid file type uploaded", { 
        fileType: file.type, 
        validTypes,
        fileName: file.name 
      });
      return NextResponse.json(
        { error: "Invalid file type. Only JPG, PNG, and WebP are allowed." },
        { status: 400 }
      );
    }

    // 2. Prepare Storage Path
    const bytes = await file.arrayBuffer();
    const buffer = Buffer.from(bytes);

    const uploadDir = join(process.cwd(), "public", "uploads");
    const filename = `${Date.now()}-${file.name.replace(/\s+/g, "-")}`;
    const path = join(uploadDir, filename);

    // 3. Store Temporarily
    await writeFile(path, buffer);
    logger.info("File uploaded successfully", { 
      filePath: path, 
      fileSize: file.size,
      fileName: filename 
    });

    // 4. Return Dummy Prediction
    // This mocks the future ResNet18 model output
    const predictionResponse = {
      success: true,
      prediction: "moi moi",
      confidence: 0.982,
      metadata: {
        filename: filename,
        size: file.size,
        type: file.type,
      },
    };

    logger.info("Prediction completed", { 
      prediction: predictionResponse.prediction,
      confidence: predictionResponse.confidence 
    });

    return NextResponse.json(predictionResponse);
  } catch (error) {
    logger.logErrorWithTraceback("Upload Error", error as Error);
    return NextResponse.json(
      { error: "Internal Server Error" },
      { status: 500 }
    );
  }
}

export const POST = withLogging(predictHandler);
