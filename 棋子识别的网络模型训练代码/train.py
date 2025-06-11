import torch
import random
from PIL import Image
import torch.nn as nn
import torch.optim as optim
from torchvision import datasets, transforms
from torch.utils.data import DataLoader
from torch.optim.lr_scheduler import StepLR


# 定义 10 层卷积神经网络
class ChineseChessCNN(nn.Module):
    def __init__(self, num_classes=14):
        super(ChineseChessCNN, self).__init__()
        self.conv_layers = nn.Sequential(
            nn.Conv2d(3, 16, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.Conv2d(16, 16, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(16, 32, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.Conv2d(32, 32, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(32, 64, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.Conv2d(64, 64, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(64, 128, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.Conv2d(128, 128, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(128, 256, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.Conv2d(256, 256, kernel_size=3, padding=1),
            nn.ReLU()
        )
        self.fc_layers = nn.Sequential(
            nn.Linear(256 * 3 * 3, 512),
            nn.ReLU(),
            nn.Linear(512, num_classes)
        )

    def forward(self, x):
        x = self.conv_layers(x)
        x = x.view(-1, 256 * 3 * 3)
        x = self.fc_layers(x)
        return x




# 数据预处理
# 数据预处理和增强
# 自定义中心随机裁剪函数
class CenterRandomCrop:
    def __init__(self, min_ratio=0.9, max_ratio=1.0):
        self.min_ratio = min_ratio
        self.max_ratio = max_ratio

    def __call__(self, img):
        width, height = img.size
        ratio = random.uniform(self.min_ratio, self.max_ratio)
        new_width = int(width * ratio)
        new_height = int(height * ratio)
        left = (width - new_width) // 2
        top = (height - new_height) // 2
        right = left + new_width
        bottom = top + new_height
        return img.crop((left, top, right, bottom))

# 自定义平移变换类
class RandomTranslation:
    def __init__(self, max_percentage=0.1):
        self.max_percentage = max_percentage

    def __call__(self, img):
        width, height = img.size
        max_x_shift = int(width * self.max_percentage)
        max_y_shift = int(height * self.max_percentage)
        x_shift = random.randint(-max_x_shift, max_x_shift)
        y_shift = random.randint(-max_y_shift, max_y_shift)
        translation_matrix = (1, 0, x_shift, 0, 1, y_shift)
        return img.transform(img.size, Image.AFFINE, translation_matrix, resample=Image.BICUBIC)

train_transform = transforms.Compose([
    CenterRandomCrop(min_ratio=0.9, max_ratio=1.0),
    RandomTranslation(max_percentage=0.1),
    transforms.RandomRotation(15),
    transforms.RandomHorizontalFlip(),
    transforms.RandomVerticalFlip(),
    transforms.ColorJitter(brightness=0.1, contrast=0.1, saturation=0.1, hue=0.1),
    transforms.Resize((54, 54)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

test_transform = transforms.Compose([
    transforms.Resize((54, 54)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

# 加载数据集
train_dataset = datasets.ImageFolder(root='data/train', transform=train_transform)
test_dataset = datasets.ImageFolder(root='data/test', transform=test_transform)

# 创建数据加载器
train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True)
test_loader = DataLoader(test_dataset, batch_size=32, shuffle=False)



# 打印类别和对应的标签
for class_name, class_idx in train_dataset.class_to_idx.items():
    print(f'类别: {class_name}, 标签: {class_idx}')


# 初始化模型、损失函数和优化器
model = ChineseChessCNN()
criterion = nn.CrossEntropyLoss()
optimizer = optim.Adam(model.parameters(), lr=0.001)

# 学习率调度器
scheduler = StepLR(optimizer, step_size=2000, gamma=0.9)

# 训练模型
num_epochs = 50000
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model.to(device)

for epoch in range(num_epochs):
    model.train()
    running_loss = 0.0
    for i, (images, labels) in enumerate(train_loader):
        images, labels = images.to(device), labels.to(device)

        optimizer.zero_grad()
        outputs = model(images)
        loss = criterion(outputs, labels)
        loss.backward()
        optimizer.step()

        running_loss += loss.item()

    # 更新学习率
    scheduler.step()
    current_lr = optimizer.param_groups[0]['lr']
    print(f'Epoch {epoch + 1}/{num_epochs}, Loss: {running_loss / len(train_loader)}, Learning Rate: {current_lr}')

# 测试模型
model.eval()
correct = 0
total = 0
with torch.no_grad():
    for images, labels in test_loader:
        images, labels = images.to(device), labels.to(device)
        outputs = model(images)
        _, predicted = torch.max(outputs.data, 1)
        total += labels.size(0)
        correct += (predicted == labels).sum().item()

print(f'Test Accuracy: {100 * correct / total}%')

# 保存模型
torch.save(model.state_dict(), 'chinese_chess_model.pth')
print("模型已保存为 chinese_chess_model.pth")
    