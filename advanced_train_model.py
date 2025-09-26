"""
高级汽车角度分类模型训练 - 目标准确率95%+
"""
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader, WeightedRandomSampler
import torchvision.transforms as transforms
from PIL import Image
import os
import json
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix
import numpy as np
from tqdm import tqdm
import matplotlib.pyplot as plt
import seaborn as sns
from collections import Counter
import torchvision.models as models
from torch.optim.lr_scheduler import CosineAnnealingWarmRestarts, OneCycleLR
import torch.nn.functional as F

from config import LABEL_CONFIG, DATA_CONFIG

class AdvancedCarAngleDataset(Dataset):
    """高级汽车角度数据集 - 支持更多数据增强"""
    def __init__(self, image_paths, labels, transform=None, is_training=True):
        self.image_paths = image_paths
        self.labels = labels
        self.transform = transform
        self.is_training = is_training
        
    def __len__(self):
        return len(self.image_paths)
    
    def __getitem__(self, idx):
        image_path = self.image_paths[idx]
        label = self.labels[idx]
        
        # 加载图片
        image = Image.open(image_path).convert('RGB')
        
        if self.transform:
            image = self.transform(image)
        
        return image, label

class AttentionModule(nn.Module):
    """注意力模块"""
    def __init__(self, in_channels):
        super(AttentionModule, self).__init__()
        self.attention = nn.Sequential(
            nn.AdaptiveAvgPool2d(1),
            nn.Conv2d(in_channels, in_channels // 16, 1),
            nn.ReLU(inplace=True),
            nn.Conv2d(in_channels // 16, in_channels, 1),
            nn.Sigmoid()
        )
    
    def forward(self, x):
        attention_weights = self.attention(x)
        return x * attention_weights

class AdvancedCarAngleClassifier(nn.Module):
    """高级汽车角度分类器 - 使用EfficientNet + 注意力机制"""
    def __init__(self, num_classes=24, model_name='efficientnet_b3'):
        super(AdvancedCarAngleClassifier, self).__init__()
        
        # 使用EfficientNet作为骨干网络
        if model_name == 'efficientnet_b3':
            self.backbone = models.efficientnet_b3(pretrained=True)
            feature_dim = 1536
        elif model_name == 'efficientnet_b4':
            self.backbone = models.efficientnet_b4(pretrained=True)
            feature_dim = 1792
        else:  # 回退到ResNet50
            self.backbone = models.resnet50(pretrained=True)
            feature_dim = 2048
        
        # 添加注意力机制
        self.attention = AttentionModule(feature_dim)
        
        # 替换分类头
        self.classifier = nn.Sequential(
            nn.AdaptiveAvgPool2d(1),
            nn.Flatten(),
            nn.Dropout(0.5),
            nn.Linear(feature_dim, 1024),
            nn.BatchNorm1d(1024),
            nn.ReLU(inplace=True),
            nn.Dropout(0.3),
            nn.Linear(1024, 512),
            nn.BatchNorm1d(512),
            nn.ReLU(inplace=True),
            nn.Dropout(0.2),
            nn.Linear(512, num_classes)
        )
        
        # 冻结早期层，只训练后面的层
        self._freeze_early_layers()
    
    def _freeze_early_layers(self):
        """冻结早期层"""
        if hasattr(self.backbone, 'features'):
            # EfficientNet
            for i, layer in enumerate(self.backbone.features):
                if i < len(self.backbone.features) - 3:  # 只训练最后3层
                    for param in layer.parameters():
                        param.requires_grad = False
        else:
            # ResNet
            for param in self.backbone.parameters():
                param.requires_grad = False
            # 解冻最后几层
            for param in self.backbone.layer4.parameters():
                param.requires_grad = True
    
    def forward(self, x):
        # 提取特征
        if hasattr(self.backbone, 'features'):
            # EfficientNet
            features = self.backbone.features(x)
        else:
            # ResNet
            features = self.backbone.conv1(x)
            features = self.backbone.bn1(features)
            features = self.backbone.relu(features)
            features = self.backbone.maxpool(features)
            features = self.backbone.layer1(features)
            features = self.backbone.layer2(features)
            features = self.backbone.layer3(features)
            features = self.backbone.layer4(features)
        
        # 应用注意力机制
        features = self.attention(features)
        
        # 分类
        output = self.classifier(features)
        return output

class FocalLoss(nn.Module):
    """Focal Loss - 处理类别不平衡"""
    def __init__(self, alpha=1, gamma=2, reduction='mean'):
        super(FocalLoss, self).__init__()
        self.alpha = alpha
        self.gamma = gamma
        self.reduction = reduction
    
    def forward(self, inputs, targets):
        ce_loss = F.cross_entropy(inputs, targets, reduction='none')
        pt = torch.exp(-ce_loss)
        focal_loss = self.alpha * (1 - pt) ** self.gamma * ce_loss
        
        if self.reduction == 'mean':
            return focal_loss.mean()
        elif self.reduction == 'sum':
            return focal_loss.sum()
        else:
            return focal_loss

class AdvancedCarAngleTrainer:
    """高级汽车角度模型训练器"""
    def __init__(self):
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        print(f"🔧 使用设备: {self.device}")
        
        # 高级数据变换
        self.train_transform = transforms.Compose([
            transforms.Resize((300, 300)),  # 更大的输入尺寸
            transforms.RandomResizedCrop(256, scale=(0.8, 1.0)),
            transforms.RandomHorizontalFlip(p=0.5),
            transforms.RandomVerticalFlip(p=0.1),  # 某些角度可能需要垂直翻转
            transforms.RandomRotation(15),
            transforms.ColorJitter(brightness=0.3, contrast=0.3, saturation=0.3, hue=0.1),
            transforms.RandomAffine(degrees=0, translate=(0.1, 0.1), scale=(0.9, 1.1)),
            transforms.RandomPerspective(distortion_scale=0.2, p=0.3),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
            transforms.RandomErasing(p=0.2, scale=(0.02, 0.1), ratio=(0.3, 3.3))
        ])
        
        self.val_transform = transforms.Compose([
            transforms.Resize((256, 256)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])
        
        # 标签映射
        self.angle_labels = LABEL_CONFIG["angles"]
        self.label_to_idx = {label: idx for idx, label in enumerate(self.angle_labels)}
        self.idx_to_label = {idx: label for label, idx in self.label_to_idx.items()}
        
        print(f"📊 标签类别: {len(self.angle_labels)}")
    
    def load_dataset(self):
        """加载数据集"""
        print("📁 加载各标签素材数据集...")
        
        image_paths = []
        labels = []
        
        # 扫描各标签素材文件夹
        angle_samples_path = DATA_CONFIG["angle_samples"]
        
        for angle_label in self.angle_labels:
            angle_path = angle_samples_path / angle_label
            if angle_path.exists():
                # 获取该角度下的所有图片
                for ext in ['*.jpg', '*.jpeg', '*.png']:
                    for img_path in angle_path.glob(ext):
                        image_paths.append(str(img_path))
                        labels.append(self.label_to_idx[angle_label])
                
                count = len(list(angle_path.glob('*.jpg')) + list(angle_path.glob('*.jpeg')) + list(angle_path.glob('*.png')))
                print(f"  📁 {angle_label}: {count} 张图片")
        
        print(f"✅ 总共加载 {len(image_paths)} 张图片")
        return image_paths, labels
    
    def create_weighted_sampler(self, labels):
        """创建加权采样器处理类别不平衡"""
        class_counts = Counter(labels)
        total_samples = len(labels)
        
        # 计算每个类别的权重
        class_weights = {}
        for class_id, count in class_counts.items():
            class_weights[class_id] = total_samples / (len(class_counts) * count)
        
        # 为每个样本分配权重
        sample_weights = [class_weights[label] for label in labels]
        
        return WeightedRandomSampler(
            weights=sample_weights,
            num_samples=len(sample_weights),
            replacement=True
        )
    
    def create_data_loaders(self, image_paths, labels, test_size=0.2, batch_size=16):
        """创建数据加载器"""
        print("📊 创建训练和验证数据集...")
        
        # 分割数据集
        train_paths, val_paths, train_labels, val_labels = train_test_split(
            image_paths, labels, test_size=test_size, random_state=42, stratify=labels
        )
        
        print(f"  训练集: {len(train_paths)} 张图片")
        print(f"  验证集: {len(val_paths)} 张图片")
        
        # 创建数据集
        train_dataset = AdvancedCarAngleDataset(train_paths, train_labels, self.train_transform, is_training=True)
        val_dataset = AdvancedCarAngleDataset(val_paths, val_labels, self.val_transform, is_training=False)
        
        # 创建加权采样器
        train_sampler = self.create_weighted_sampler(train_labels)
        
        # 创建数据加载器
        train_loader = DataLoader(
            train_dataset, 
            batch_size=batch_size, 
            sampler=train_sampler,
            num_workers=4,
            pin_memory=True
        )
        val_loader = DataLoader(
            val_dataset, 
            batch_size=batch_size, 
            shuffle=False, 
            num_workers=4,
            pin_memory=True
        )
        
        return train_loader, val_loader
    
    def train_model(self, train_loader, val_loader, num_epochs=100, learning_rate=0.001):
        """训练模型"""
        print("🚀 开始训练高级模型...")
        
        # 创建模型
        model = AdvancedCarAngleClassifier(num_classes=len(self.angle_labels))
        model = model.to(self.device)
        
        # 损失函数 - 使用Focal Loss处理类别不平衡
        criterion = FocalLoss(alpha=1, gamma=2)
        
        # 优化器 - 使用AdamW
        optimizer = optim.AdamW(
            model.parameters(), 
            lr=learning_rate, 
            weight_decay=0.01,
            betas=(0.9, 0.999)
        )
        
        # 学习率调度器 - 使用OneCycleLR
        scheduler = OneCycleLR(
            optimizer,
            max_lr=learning_rate * 10,
            epochs=num_epochs,
            steps_per_epoch=len(train_loader),
            pct_start=0.1,
            anneal_strategy='cos'
        )
        
        # 训练历史
        train_losses = []
        val_losses = []
        train_accuracies = []
        val_accuracies = []
        
        best_val_acc = 0.0
        best_model_state = None
        patience = 15
        patience_counter = 0
        
        for epoch in range(num_epochs):
            # 训练阶段
            model.train()
            train_loss = 0.0
            train_correct = 0
            train_total = 0
            
            train_pbar = tqdm(train_loader, desc=f'Epoch {epoch+1}/{num_epochs} [Train]')
            for batch_idx, (images, labels) in enumerate(train_pbar):
                images, labels = images.to(self.device), labels.to(self.device)
                
                optimizer.zero_grad()
                outputs = model(images)
                loss = criterion(outputs, labels)
                loss.backward()
                
                # 梯度裁剪
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                
                optimizer.step()
                scheduler.step()
                
                train_loss += loss.item()
                _, predicted = torch.max(outputs.data, 1)
                train_total += labels.size(0)
                train_correct += (predicted == labels).sum().item()
                
                train_pbar.set_postfix({
                    'Loss': f'{loss.item():.4f}',
                    'Acc': f'{100 * train_correct / train_total:.2f}%',
                    'LR': f'{scheduler.get_last_lr()[0]:.6f}'
                })
            
            # 验证阶段
            model.eval()
            val_loss = 0.0
            val_correct = 0
            val_total = 0
            
            with torch.no_grad():
                val_pbar = tqdm(val_loader, desc=f'Epoch {epoch+1}/{num_epochs} [Val]')
                for images, labels in val_pbar:
                    images, labels = images.to(self.device), labels.to(self.device)
                    outputs = model(images)
                    loss = criterion(outputs, labels)
                    
                    val_loss += loss.item()
                    _, predicted = torch.max(outputs.data, 1)
                    val_total += labels.size(0)
                    val_correct += (predicted == labels).sum().item()
                    
                    val_pbar.set_postfix({
                        'Loss': f'{loss.item():.4f}',
                        'Acc': f'{100 * val_correct / val_total:.2f}%'
                    })
            
            # 计算平均损失和准确率
            avg_train_loss = train_loss / len(train_loader)
            avg_val_loss = val_loss / len(val_loader)
            train_acc = 100 * train_correct / train_total
            val_acc = 100 * val_correct / val_total
            
            train_losses.append(avg_train_loss)
            val_losses.append(avg_val_loss)
            train_accuracies.append(train_acc)
            val_accuracies.append(val_acc)
            
            # 保存最佳模型
            if val_acc > best_val_acc:
                best_val_acc = val_acc
                best_model_state = model.state_dict().copy()
                patience_counter = 0
            else:
                patience_counter += 1
            
            print(f'Epoch {epoch+1}/{num_epochs}:')
            print(f'  Train Loss: {avg_train_loss:.4f}, Train Acc: {train_acc:.2f}%')
            print(f'  Val Loss: {avg_val_loss:.4f}, Val Acc: {val_acc:.2f}%')
            print(f'  Best Val Acc: {best_val_acc:.2f}%')
            print(f'  Patience: {patience_counter}/{patience}')
            print('-' * 50)
            
            # 早停
            if patience_counter >= patience:
                print(f"🛑 早停触发，最佳验证准确率: {best_val_acc:.2f}%")
                break
        
        # 加载最佳模型
        if best_model_state:
            model.load_state_dict(best_model_state)
        
        # 保存训练历史
        self.save_training_history(train_losses, val_losses, train_accuracies, val_accuracies)
        
        return model, best_val_acc
    
    def save_training_history(self, train_losses, val_losses, train_accuracies, val_accuracies):
        """保存训练历史"""
        history = {
            'train_losses': train_losses,
            'val_losses': val_losses,
            'train_accuracies': train_accuracies,
            'val_accuracies': val_accuracies
        }
        
        history_path = DATA_CONFIG["models"] / "advanced_training_history.json"
        with open(history_path, 'w') as f:
            json.dump(history, f, indent=2)
        
        print(f"📊 训练历史已保存到: {history_path}")
    
    def evaluate_model(self, model, val_loader):
        """评估模型"""
        print("📊 评估模型性能...")
        
        model.eval()
        all_predictions = []
        all_labels = []
        
        with torch.no_grad():
            for images, labels in tqdm(val_loader, desc="评估中"):
                images, labels = images.to(self.device), labels.to(self.device)
                outputs = model(images)
                _, predicted = torch.max(outputs, 1)
                
                all_predictions.extend(predicted.cpu().numpy())
                all_labels.extend(labels.cpu().numpy())
        
        # 计算分类报告
        unique_labels = sorted(set(all_labels))
        target_names = [self.idx_to_label[i] for i in unique_labels]
        report = classification_report(all_labels, all_predictions, target_names=target_names, labels=unique_labels)
        print("\n📋 分类报告:")
        print(report)
        
        # 计算混淆矩阵
        cm = confusion_matrix(all_labels, all_predictions)
        
        # 保存评估结果
        eval_results = {
            'classification_report': report,
            'confusion_matrix': cm.tolist(),
            'accuracy': (np.array(all_predictions) == np.array(all_labels)).mean()
        }
        
        eval_path = DATA_CONFIG["models"] / "advanced_evaluation_results.json"
        with open(eval_path, 'w') as f:
            json.dump(eval_results, f, indent=2)
        
        print(f"📊 评估结果已保存到: {eval_path}")
        
        return eval_results
    
    def save_model(self, model, accuracy):
        """保存模型"""
        model_path = DATA_CONFIG["models"] / "advanced_car_angle_classifier.pth"
        
        # 保存模型状态和元数据
        model_data = {
            'model_state_dict': model.state_dict(),
            'num_classes': len(self.angle_labels),
            'angle_labels': self.angle_labels,
            'label_to_idx': self.label_to_idx,
            'idx_to_label': self.idx_to_label,
            'accuracy': accuracy,
            'model_architecture': 'EfficientNet-B3 + Attention'
        }
        
        torch.save(model_data, model_path)
        print(f"💾 模型已保存到: {model_path}")
        print(f"📊 最佳验证准确率: {accuracy:.2f}%")
        
        return model_path

def main():
    """主函数"""
    print("🚗 高级汽车角度分类模型训练 - 目标准确率95%+")
    print("=" * 60)
    
    # 创建训练器
    trainer = AdvancedCarAngleTrainer()
    
    # 加载数据集
    image_paths, labels = trainer.load_dataset()
    
    if len(image_paths) == 0:
        print("❌ 没有找到训练数据，请检查各标签素材文件夹")
        return
    
    # 创建数据加载器
    train_loader, val_loader = trainer.create_data_loaders(image_paths, labels, batch_size=32)
    
    # 训练模型
    model, best_acc = trainer.train_model(train_loader, val_loader, num_epochs=100)
    
    # 评估模型
    eval_results = trainer.evaluate_model(model, val_loader)
    
    # 保存模型
    model_path = trainer.save_model(model, best_acc)
    
    print(f"\n✅ 高级模型训练完成!")
    print(f"📁 模型保存位置: {model_path}")
    print(f"📊 最佳准确率: {best_acc:.2f}%")
    
    if best_acc >= 95.0:
        print("🎉 恭喜！达到目标准确率95%+")
    else:
        print(f"📈 当前准确率: {best_acc:.2f}%，距离目标95%还需提升: {95.0 - best_acc:.2f}%")

if __name__ == "__main__":
    main()
