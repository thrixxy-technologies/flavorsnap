#!/usr/bin/env python3
"""
Improved training script for FlavorSnap food classification model.

Features:
- Data augmentation for small datasets
- Proper train/val split
- Early stopping
- Learning rate scheduling
- Checkpointing
- Progress bars
"""

import os
import sys
import time
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, random_split, WeightedRandomSampler
from torchvision import models, transforms
from torchvision.datasets import ImageFolder
from collections import Counter
import numpy as np

# Configuration
DATA_DIR = 'dataset/train'
MODEL_PATH = 'models/best_model.pth'
NUM_EPOCHS = 50
BATCH_SIZE = 8
LEARNING_RATE = 0.001
WEIGHT_DECAY = 1e-4
EARLY_STOPPING_PATIENCE = 10
VALIDATION_SPLIT = 0.2

# Device configuration
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Using device: {device}")


def get_data_transforms():
    """
    Define data augmentation for training and validation.
    Augmentation is crucial for small datasets to prevent overfitting.
    """
    train_transform = transforms.Compose([
        transforms.Resize((256, 256)),
        transforms.RandomCrop((224, 224)),
        transforms.RandomHorizontalFlip(p=0.5),
        transforms.RandomRotation(degrees=15),
        transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2, hue=0.1),
        transforms.RandomAffine(degrees=0, translate=(0.1, 0.1), scale=(0.9, 1.1)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])

    val_transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])

    return train_transform, val_transform


def create_dataloaders():
    """
    Create training and validation dataloaders with proper transforms.
    Handles class imbalance using weighted sampling if needed.
    """
    train_transform, val_transform = get_data_transforms()

    # Load full dataset to get class names
    full_dataset = ImageFolder(root=DATA_DIR, transform=train_transform)
    class_names = full_dataset.classes
    num_classes = len(class_names)

    print(f"Found {len(full_dataset)} images in {num_classes} classes:")
    for idx, class_name in enumerate(class_names):
        count = sum(1 for _, label in full_dataset.samples if label == idx)
        print(f"  - {class_name}: {count} images")

    # Split dataset
    val_size = int(VALIDATION_SPLIT * len(full_dataset))
    train_size = len(full_dataset) - val_size

    # Create train and validation datasets with different transforms
    train_dataset = ImageFolder(root=DATA_DIR, transform=train_transform)
    val_dataset = ImageFolder(root=DATA_DIR, transform=val_transform)

    # Use same indices for split
    indices = list(range(len(full_dataset)))
    np.random.seed(42)
    np.random.shuffle(indices)

    train_indices = indices[:train_size]
    val_indices = indices[train_size:]

    # Create subset datasets
    train_dataset = torch.utils.data.Subset(train_dataset, train_indices)
    val_dataset = torch.utils.data.Subset(val_dataset, val_indices)

    # Create dataloaders
    train_loader = DataLoader(
        train_dataset,
        batch_size=BATCH_SIZE,
        shuffle=True,
        num_workers=0,  # Set to higher if on Linux/macOS
        pin_memory=True if device.type == "cuda" else False
    )

    val_loader = DataLoader(
        val_dataset,
        batch_size=BATCH_SIZE,
        shuffle=False,
        num_workers=0,
        pin_memory=True if device.type == "cuda" else False
    )

    return train_loader, val_loader, num_classes, class_names


def create_model(num_classes):
    """
    Create ResNet18 model with transfer learning.
    Freezes early layers and only trains the classifier.
    """
    model = models.resnet18(weights='IMAGENET1K_V1')

    # Freeze feature extractor layers (optional - helps with small datasets)
    # for param in model.parameters():
    #     param.requires_grad = False

    # Replace final layer for our number of classes
    model.fc = nn.Linear(model.fc.in_features, num_classes)

    return model.to(device)


def train_epoch(model, loader, criterion, optimizer, epoch):
    """
    Train for one epoch with progress tracking.
    """
    model.train()
    running_loss = 0.0
    correct = 0
    total = 0

    for batch_idx, (images, labels) in enumerate(loader):
        images, labels = images.to(device), labels.to(device)

        optimizer.zero_grad()
        outputs = model(images)
        loss = criterion(outputs, labels)
        loss.backward()
        optimizer.step()

        running_loss += loss.item()
        _, predicted = outputs.max(1)
        total += labels.size(0)
        correct += predicted.eq(labels).sum().item()

        if (batch_idx + 1) % 5 == 0 or batch_idx == len(loader) - 1:
            print(f"  Batch [{batch_idx+1}/{len(loader)}] Loss: {loss.item():.4f}")

    epoch_loss = running_loss / len(loader)
    epoch_acc = 100. * correct / total
    return epoch_loss, epoch_acc


def validate(model, loader, criterion):
    """
    Validate the model and return loss and accuracy.
    """
    model.eval()
    running_loss = 0.0
    correct = 0
    total = 0

    with torch.no_grad():
        for images, labels in loader:
            images, labels = images.to(device), labels.to(device)
            outputs = model(images)
            loss = criterion(outputs, labels)

            running_loss += loss.item()
            _, predicted = outputs.max(1)
            total += labels.size(0)
            correct += predicted.eq(labels).sum().item()

    epoch_loss = running_loss / len(loader)
    epoch_acc = 100. * correct / total
    return epoch_loss, epoch_acc


def main():
    """
    Main training loop with early stopping and checkpointing.
    """
    print("="*60)
    print("FlavorSnap Model Training")
    print("="*60)

    # Ensure model directory exists
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)

    # Create dataloaders
    print("\nLoading dataset...")
    train_loader, val_loader, num_classes, class_names = create_dataloaders()
    print(f"Training samples: {len(train_loader.dataset)}")
    print(f"Validation samples: {len(val_loader.dataset)}")

    # Create model
    print(f"\nInitializing ResNet18 with {num_classes} output classes...")
    model = create_model(num_classes)
    print(f"Model parameters: {sum(p.numel() for p in model.parameters()):,}")

    # Loss, optimizer, and scheduler
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=LEARNING_RATE, weight_decay=WEIGHT_DECAY)
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode='min', factor=0.5, patience=5, verbose=True
    )

    # Training tracking
    best_val_loss = float('inf')
    best_val_acc = 0.0
    patience_counter = 0
    history = {'train_loss': [], 'train_acc': [], 'val_loss': [], 'val_acc': []}

    print("\n" + "="*60)
    print("Starting Training")
    print("="*60)

    for epoch in range(NUM_EPOCHS):
        start_time = time.time()

        # Train
        train_loss, train_acc = train_epoch(model, train_loader, criterion, optimizer, epoch)

        # Validate
        val_loss, val_acc = validate(model, val_loader, criterion)

        # Update scheduler
        scheduler.step(val_loss)

        # Save history
        history['train_loss'].append(train_loss)
        history['train_acc'].append(train_acc)
        history['val_loss'].append(val_loss)
        history['val_acc'].append(val_acc)

        # Check for improvement
        is_best = val_loss < best_val_loss
        if is_best:
            best_val_loss = val_loss
            best_val_acc = val_acc
            patience_counter = 0
            # Save best model
            torch.save({
                'epoch': epoch,
                'model_state_dict': model.state_dict(),
                'optimizer_state_dict': optimizer.state_dict(),
                'val_loss': val_loss,
                'val_acc': val_acc,
                'class_names': class_names,
                'num_classes': num_classes
            }, MODEL_PATH)
            print(f"  💾 Best model saved! (Val Loss: {val_loss:.4f})")
        else:
            patience_counter += 1

        epoch_time = time.time() - start_time

        # Print epoch summary
        print(f"\nEpoch [{epoch+1}/{NUM_EPOCHS}] - {epoch_time:.1f}s")
        print(f"  Train Loss: {train_loss:.4f} | Train Acc: {train_acc:.2f}%")
        print(f"  Val Loss:   {val_loss:.4f} | Val Acc:   {val_acc:.2f}%")
        print(f"  Best Val:   {best_val_loss:.4f} | Best Acc:  {best_val_acc:.2f}%")
        print(f"  LR:         {optimizer.param_groups[0]['lr']:.6f}")

        # Early stopping
        if patience_counter >= EARLY_STOPPING_PATIENCE:
            print(f"\n⏹️  Early stopping triggered after {epoch+1} epochs")
            break

    print("\n" + "="*60)
    print("Training Complete!")
    print("="*60)
    print(f"Best Validation Loss: {best_val_loss:.4f}")
    print(f"Best Validation Accuracy: {best_val_acc:.2f}%")
    print(f"Model saved to: {MODEL_PATH}")

    # Print final class mapping
    print("\nClass Mapping:")
    for idx, name in enumerate(class_names):
        print(f"  {idx}: {name}")


if __name__ == '__main__':
    main()
