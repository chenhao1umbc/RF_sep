""" Full assembly of the parts to form the complete network """

import torch.nn.functional as F
import torch.nn as nn
from .unet_parts import *


class UNet(nn.Module):
    def __init__(self, n_channels, n_classes, bilinear=True):
        super(UNet, self).__init__()
        self.n_channels = n_channels
        self.n_classes = n_classes
        self.bilinear = bilinear

        self.inc = DoubleConv(n_channels, 64)
        self.down1 = Down(64, 128)
        self.down2 = Down(128, 256)
        self.down3 = Down(256, 512)
        factor = 2 if bilinear else 1
        self.down4 = Down(512, 1024 // factor)
        self.up1 = Up(1024, 512, bilinear)
        self.up2 = Up(512, 256, bilinear)
        self.up3 = Up(256, 128, bilinear)
        self.up4 = Up(128, 64 * factor, bilinear)
        self.outc = OutConv(64, n_classes)
        self.sigmoid = nn.Sigmoid()

    def forward(self, x):
        x1 = self.inc(x)
        x2 = self.down1(x1)
        x3 = self.down2(x2)
        x4 = self.down3(x3)
        x5 = self.down4(x4)
        x = self.up1(x5, x4)
        x = self.up2(x, x3)
        x = self.up3(x, x2)
        x = self.up4(x, x1)
        logits = self.outc(x)
        return logits


class Up_(nn.Module):
    """Upscaling then double conv"""

    def __init__(self, in_channels, out_channels, bilinear=True):
        super().__init__()

        # if bilinear, use the normal convolutions to reduce the number of channels
        if bilinear:
            # self.up = nn.Upsample(scale_factor=2, mode='bilinear', align_corners=True)
            # self.conv = DoubleConv(in_channels, out_channels // 2, in_channels // 2)
            self.up = nn.ConvTranspose2d(in_channels , in_channels, kernel_size=2, stride=2)
            self.conv = DoubleConv(in_channels, out_channels)
        else:
            self.up = nn.ConvTranspose2d(in_channels , in_channels // 2, kernel_size=2, stride=2)
            self.conv = DoubleConv(in_channels//2, out_channels)

    def forward(self, x):
        x = self.up(x)
        return self.conv(x)


class MyUp(nn.Module):
    """Upscaling then double conv"""

    def __init__(self, in_channels, out_channels):
        super().__init__()
        self.up = nn.ConvTranspose2d(in_channels , in_channels // 2, kernel_size=2, stride=2)
        self.conv = DoubleConv(in_channels//2, out_channels)

    def forward(self, x):
        x = self.up(x)
        return self.conv(x)


class UNetHalf4to150(nn.Module):
    def __init__(self, n_channels, n_classes, bilinear=False):
        """Only the up part of the unet

        Args:
            n_channels ([type]): [how many input channels=n_sources]
            n_classes ([type]): [how many output classes=n_sources]
            bilinear (bool, optional): [use interpolation or deconv]. Defaults to False(use deconv).
        """
        super(UNetHalf4to150, self).__init__()
        self.n_ch = n_channels
        self.n_classes = n_classes
        self.bilinear = bilinear
        self.n_ch = 128

        self.inc = DoubleConv(n_channels, self.n_ch)
        self.up1 = Up_(self.n_ch, self.n_ch//2, bilinear=True)
        self.up2 = Up_(self.n_ch//2, self.n_ch//4, bilinear)
        self.up3 = Up_(self.n_ch//4, self.n_ch//8, bilinear)
        self.up4 = Up_(self.n_ch//8, self.n_ch//16, bilinear)
        self.up5 = Up_(self.n_ch//16, self.n_ch//32, bilinear)
        self.up6 = Up_(self.n_ch//32, self.n_ch//32, bilinear)
        self.reshape = nn.Sequential(
            nn.Conv2d(self.n_ch//32, self.n_ch//16, kernel_size=3, padding=1, stride=2),
            nn.ConvTranspose2d(self.n_ch//16, 16, kernel_size=5, dilation=3, output_padding=2),
            nn.BatchNorm2d(16),
            nn.LeakyReLU(inplace=True),
            nn.ConvTranspose2d(16, 16, kernel_size=3, dilation=3, output_padding=2),
            nn.Conv2d(16, 16, kernel_size=3, padding=1),
            nn.BatchNorm2d(16),
            nn.LeakyReLU(inplace=True))
        self.outc = OutConv(16, n_classes)

    def forward(self, x):
        x = self.inc(x)
        x = self.up1(x)
        x = self.up2(x)
        x = self.up3(x)
        x = self.up4(x)  # output has W=256, H=256, for gamma = 16
        x = self.up5(x) # input has W=32, H=32, for gamma = 2
        x = self.up6(x)
        x = self.reshape(x) # input 256 output 150
        out = self.outc(x)
        return out


class UNetHalf4to50(nn.Module):
    def __init__(self, n_channels, n_classes, bilinear=False):
        """Only the up part of the unet

        Args:
            n_channels ([type]): [how many input channels=n_sources]
            n_classes ([type]): [how many output classes=n_sources]
            bilinear (bool, optional): [use interpolation or deconv]. Defaults to False(use deconv).
        """
        super(UNetHalf4to50, self).__init__()
        self.n_ch = n_channels
        self.n_classes = n_classes
        self.bilinear = bilinear
        self.n_ch = 128

        self.inc = DoubleConv(n_channels, self.n_ch)
        self.up1 = Up_(self.n_ch, self.n_ch//2, bilinear=True)
        self.up2 = Up_(self.n_ch//2, self.n_ch//4, bilinear)
        self.up3 = Up_(self.n_ch//4, self.n_ch//8, bilinear)
        self.up4 = Up_(self.n_ch//8, self.n_ch//16, bilinear)
        self.reshape = nn.Sequential(
            nn.Conv2d(self.n_ch//16, self.n_ch//16, kernel_size=3, padding=1, stride=2),
            nn.ConvTranspose2d(self.n_ch//16, 16, kernel_size=5, dilation=3, output_padding=1),
            nn.BatchNorm2d(16),
            nn.LeakyReLU(inplace=True),
            nn.ConvTranspose2d(16, 16, kernel_size=3, dilation=3, output_padding=1),
            nn.Conv2d(16, 32, kernel_size=3, padding=0),
            nn.BatchNorm2d(32),
            nn.LeakyReLU(inplace=True))
        self.outc = OutConv(32, n_classes)

    def forward(self, x):
        x = self.inc(x)
        x = self.up1(x)
        x = self.up2(x)
        x = self.up3(x)
        x = self.up4(x)  # output has W=256, H=256, for gamma = 16
        x = self.reshape(x) # input 256 output 150
        out = self.outc(x)
        return out


class UNetHalf8to50(nn.Module):
    def __init__(self, n_channels, n_classes, bilinear=False):
        """Only the up part of the unet
        Args:
            n_channels ([type]): [how many input channels=n_sources]
            n_classes ([type]): [how many output classes=n_sources]
            bilinear (bool, optional): [use interpolation or deconv]. Defaults to False(use deconv).
        """
        super(UNetHalf8to50, self).__init__()
        self.n_ch = n_channels
        self.n_classes = n_classes
        self.bilinear = bilinear
        self.n_ch = 128

        self.inc = DoubleConv(n_channels, self.n_ch)
        self.up1 = Up_(self.n_ch, self.n_ch//2, bilinear=True)
        self.up2 = Up_(self.n_ch//2, self.n_ch//4, bilinear)
        self.up3 = Up_(self.n_ch//4, self.n_ch//8, bilinear)
        self.reshape = nn.Sequential(
            nn.Conv2d(self.n_ch//8, self.n_ch//8, kernel_size=3, padding=1, stride=2),
            nn.ConvTranspose2d(self.n_ch//8, 16, kernel_size=5, dilation=3, output_padding=1),
            nn.BatchNorm2d(16),
            nn.LeakyReLU(inplace=True),
            nn.ConvTranspose2d(16, 16, kernel_size=3, dilation=3, output_padding=1),
            nn.Conv2d(16, 32, kernel_size=3, padding=0),
            nn.BatchNorm2d(32),
            nn.LeakyReLU(inplace=True))
        self.outc = OutConv(32, n_classes)

    def forward(self, x):
        x = self.inc(x)
        x = self.up1(x)
        x = self.up2(x)
        x = self.up3(x)
        x = self.reshape(x) # input 256 output 150
        out = self.outc(x)
        return out


class UNetHalf8to128(nn.Module):
    def __init__(self, n_channels, n_classes, bilinear=False):
        """Only the up part of the unet
        Args:
            n_channels ([type]): [how many input channels=n_sources]
            n_classes ([type]): [how many output classes=n_sources]
            bilinear (bool, optional): [use interpolation or deconv]. Defaults to False(use deconv).
        """
        super(UNetHalf8to128, self).__init__()
        self.n_ch = n_channels
        self.n_classes = n_classes
        self.bilinear = bilinear
        self.n_ch = 128

        self.inc = DoubleConv(n_channels, self.n_ch)
        self.up1 = Up_(self.n_ch, self.n_ch//2, bilinear=True)
        self.up2 = Up_(self.n_ch//2, self.n_ch//4, bilinear)
        self.up3 = Up_(self.n_ch//4, self.n_ch//8, bilinear)
        self.up4 = Up_(self.n_ch//8, self.n_ch//16, bilinear)
        self.reshape = nn.Sequential(
            nn.Conv2d(self.n_ch//16, self.n_ch//8, kernel_size=3, padding=1),
            nn.BatchNorm2d(self.n_ch//8),
            nn.LeakyReLU(inplace=True),
            nn.Conv2d(self.n_ch//8, 32, kernel_size=3, padding=1),
            nn.BatchNorm2d(32),
            nn.LeakyReLU(inplace=True))
        self.outc = OutConv(32, n_classes)

    def forward(self, x):
        x = self.inc(x)
        x = self.up1(x)
        x = self.up2(x)
        x = self.up3(x)
        x = self.up4(x)
        x = self.reshape(x) 
        out = self.outc(x)
        return out


class UNetHalf8to100(nn.Module):
    def __init__(self, n_channels, n_classes, bilinear=False):
        """Only the up part of the unet
        Args:
            n_channels ([type]): [how many input channels=n_sources]
            n_classes ([type]): [how many output classes=n_sources]
            bilinear (bool, optional): [use interpolation or deconv]. Defaults to False(use deconv).
        """
        super(UNetHalf8to100, self).__init__()
        self.n_ch = n_channels
        self.n_classes = n_classes
        self.bilinear = bilinear
        self.n_ch = 128

        self.inc = DoubleConv(n_channels, self.n_ch)
        self.up1 = Up_(self.n_ch, self.n_ch//2, bilinear=True)
        self.up2 = Up_(self.n_ch//2, self.n_ch//4, bilinear)
        self.up3 = Up_(self.n_ch//4, self.n_ch//8, bilinear)
        self.up4 = Up_(self.n_ch//8, self.n_ch//16, bilinear)
        self.reshape = nn.Sequential(
            nn.Conv2d(self.n_ch//16, self.n_ch//16, kernel_size=5, dilation=3),
            nn.Conv2d(self.n_ch//16, self.n_ch//16, kernel_size=5, dilation=3),
            nn.Conv2d(self.n_ch//16, self.n_ch//8, kernel_size=3, dilation=2),
            nn.BatchNorm2d(self.n_ch//8),
            nn.LeakyReLU(inplace=True),
            nn.Conv2d(self.n_ch//8, 32, kernel_size=3, padding=1),
            nn.BatchNorm2d(32),
            nn.LeakyReLU(inplace=True))
        self.outc = OutConv(32, n_classes)

    def forward(self, x):
        x = self.inc(x)
        x = self.up1(x)
        x = self.up2(x)
        x = self.up3(x)
        x = self.up4(x)
        x = self.reshape(x) 
        out = self.outc(x)
        return out


class UNetHalf8to100_morelayers(nn.Module):
    "16 layers here"
    def __init__(self, n_channels, n_classes, bilinear=False):
        """Only the up part of the unet
        Args:
            n_channels ([type]): [how many input channels=n_sources]
            n_classes ([type]): [how many output classes=n_sources]
            bilinear (bool, optional): [use interpolation or deconv]. Defaults to False(use deconv).
        """
        super(UNetHalf8to100_morelayers, self).__init__()
        self.n_ch = n_channels
        self.n_classes = n_classes
        self.bilinear = bilinear
        self.n_ch = 128

        self.inc = DoubleConv(n_channels, self.n_ch)
        self.up1 = Up_(self.n_ch, self.n_ch//2, bilinear=True)
        self.up2 = Up_(self.n_ch//2, self.n_ch//4, bilinear)
        self.up3 = Up_(self.n_ch//4, self.n_ch//8, bilinear)
        self.up4 = Up_(self.n_ch//8, self.n_ch//16, bilinear)
        self.reshape = nn.Sequential(
            nn.Conv2d(self.n_ch//16, self.n_ch//16, kernel_size=5, dilation=3),
            nn.BatchNorm2d(self.n_ch//16),
            nn.LeakyReLU(inplace=True),
            nn.Conv2d(self.n_ch//16, self.n_ch//16, kernel_size=5, dilation=3),
            nn.BatchNorm2d(self.n_ch//16),
            nn.LeakyReLU(inplace=True),
            nn.Conv2d(self.n_ch//16, self.n_ch//8, kernel_size=3, dilation=2),
            nn.BatchNorm2d(self.n_ch//8),
            nn.LeakyReLU(inplace=True),
            nn.Conv2d(self.n_ch//8, 32, kernel_size=3, padding=1),
            nn.BatchNorm2d(32),
            nn.LeakyReLU(inplace=True))
        self.outc = OutConv(32, n_classes)

    def forward(self, x):
        x = self.inc(x)
        x = self.up1(x)
        x = self.up2(x)
        x = self.up3(x)
        x = self.up4(x)
        x = self.reshape(x) 
        out = self.outc(x)
        return out


class UNetHalf8to100_16_FC_128(nn.Module):
    "16 layers here"
    def __init__(self, n_channels, n_classes, bilinear=False):
        """Only the up part of the unet
        Args:
            n_channels ([type]): [how many input channels=n_sources]
            n_classes ([type]): [how many output classes=n_sources]
            bilinear (bool, optional): [use interpolation or deconv]. Defaults to False(use deconv).
        """
        super(UNetHalf8to100_16_FC_128, self).__init__()
        self.n_ch = n_channels
        self.n_classes = n_classes
        self.bilinear = bilinear
        self.n_ch = 128
        
        self.fc = nn.Linear(9, 8)
        self.inc = DoubleConv(n_channels, self.n_ch)
        self.up1 = Up_(self.n_ch, self.n_ch//2, bilinear=True)
        self.up2 = Up_(self.n_ch//2, self.n_ch//4, bilinear)
        self.up3 = Up_(self.n_ch//4, self.n_ch//8, bilinear)
        self.up4 = Up_(self.n_ch//8, self.n_ch//16, bilinear)
        self.reshape = nn.Sequential(
            nn.Conv2d(self.n_ch//16, self.n_ch//16, kernel_size=5, dilation=3),
            nn.BatchNorm2d(self.n_ch//16),
            nn.LeakyReLU(inplace=True),
            nn.Conv2d(self.n_ch//16, self.n_ch//16, kernel_size=5, dilation=3),
            nn.BatchNorm2d(self.n_ch//16),
            nn.LeakyReLU(inplace=True),
            nn.Conv2d(self.n_ch//16, self.n_ch//8, kernel_size=3, dilation=2),
            nn.BatchNorm2d(self.n_ch//8),
            nn.LeakyReLU(inplace=True),
            nn.Conv2d(self.n_ch//8, 32, kernel_size=3, padding=1),
            nn.BatchNorm2d(32),
            nn.LeakyReLU(inplace=True))
        self.outc = OutConv(32, n_classes)

    def forward(self, x):
        x = self.fc(x)
        x = self.inc(x)
        x = self.up1(x)
        x = self.up2(x)
        x = self.up3(x)
        x = self.up4(x)
        x = self.reshape(x) 
        out = self.outc(x)
        return out


class UNetHalf8to100_16_FC(nn.Module):
    "16 layers here"
    def __init__(self, n_channels, n_classes, bilinear=False):
        """Only the up part of the unet
        Args:
            n_channels ([type]): [how many input channels=n_sources]
            n_classes ([type]): [how many output classes=n_sources]
            bilinear (bool, optional): [use interpolation or deconv]. Defaults to False(use deconv).
        """
        super(UNetHalf8to100_16_FC, self).__init__()
        self.n_ch = n_channels
        self.n_classes = n_classes
        self.bilinear = bilinear
        self.n_ch = 256
        
        self.fc = nn.Linear(9, 8)
        self.inc = DoubleConv(n_channels, self.n_ch)
        self.up1 = Up_(self.n_ch, self.n_ch//2, bilinear=True)
        self.up2 = Up_(self.n_ch//2, self.n_ch//4, bilinear)
        self.up3 = Up_(self.n_ch//4, self.n_ch//8, bilinear)
        self.up4 = Up_(self.n_ch//8, self.n_ch//16, bilinear)
        self.reshape = nn.Sequential(
            nn.Conv2d(self.n_ch//16, self.n_ch//16, kernel_size=5, dilation=3),
            nn.BatchNorm2d(self.n_ch//16),
            nn.LeakyReLU(inplace=True),
            nn.Conv2d(self.n_ch//16, self.n_ch//16, kernel_size=5, dilation=3),
            nn.BatchNorm2d(self.n_ch//16),
            nn.LeakyReLU(inplace=True),
            nn.Conv2d(self.n_ch//16, self.n_ch//8, kernel_size=3, dilation=2),
            nn.BatchNorm2d(self.n_ch//8),
            nn.LeakyReLU(inplace=True),
            nn.Conv2d(self.n_ch//8, 32, kernel_size=3, padding=1),
            nn.BatchNorm2d(32),
            nn.LeakyReLU(inplace=True))
        self.outc = OutConv(32, n_classes)

    def forward(self, x):
        x = self.fc(x)
        x = self.inc(x)
        x = self.up1(x)
        x = self.up2(x)
        x = self.up3(x)
        x = self.up4(x)
        x = self.reshape(x) 
        out = self.outc(x)
        return out


class UNetHalf8to100_stack(nn.Module):
    "16 layers here, input is not added noise, just stack noise and resized mixture"
    def __init__(self, n_channels, n_classes, bilinear=False):
        """Only the up part of the unet
        Args:
            n_channels ([type]): [how many input channels=n_sources]
            n_classes ([type]): [how many output classes=n_sources]
            bilinear (bool, optional): [use interpolation or deconv]. Defaults to False(use deconv).
        """
        super(UNetHalf8to100_stack, self).__init__()
        self.n_ch = n_channels
        self.n_classes = n_classes
        self.bilinear = bilinear
        self.n_ch = 128

        self.inc = DoubleConv(n_channels, self.n_ch)
        self.up1 = Up_(self.n_ch, self.n_ch//2, bilinear=True)
        self.up2 = Up_(self.n_ch//2, self.n_ch//4, bilinear)
        self.up3 = Up_(self.n_ch//4, self.n_ch//8, bilinear)
        self.up4 = Up_(self.n_ch//8, self.n_ch//16, bilinear)
        self.reshape = nn.Sequential(
            nn.Conv2d(self.n_ch//16, self.n_ch//16, kernel_size=5, dilation=3),
            nn.BatchNorm2d(self.n_ch//16),
            nn.LeakyReLU(inplace=True),
            nn.Conv2d(self.n_ch//16, self.n_ch//16, kernel_size=5, dilation=3),
            nn.BatchNorm2d(self.n_ch//16),
            nn.LeakyReLU(inplace=True),
            nn.Conv2d(self.n_ch//16, self.n_ch//8, kernel_size=3, dilation=2),
            nn.BatchNorm2d(self.n_ch//8),
            nn.LeakyReLU(inplace=True),
            nn.Conv2d(self.n_ch//8, 32, kernel_size=3, padding=1),
            nn.BatchNorm2d(32),
            nn.LeakyReLU(inplace=True))
        self.outc = OutConv(32, n_classes)

    def forward(self, x):
        x = self.inc(x)
        x = self.up1(x)
        x = self.up2(x)
        x = F.max_pool2d(x, (2,1))
        x = self.up3(x)
        x = self.up4(x)
        x = self.reshape(x) 
        out = self.outc(x)
        return out


class UNetHalf8to100_stack_256(nn.Module):
    "16 layers here, input is not added noise, just stack noise and resized mixture"
    def __init__(self, n_channels, n_classes, bilinear=False):
        """Only the up part of the unet
        Args:
            n_channels ([type]): [how many input channels=n_sources]
            n_classes ([type]): [how many output classes=n_sources]
            bilinear (bool, optional): [use interpolation or deconv]. Defaults to False(use deconv).
        """
        super(UNetHalf8to100_stack_256, self).__init__()
        self.n_ch = n_channels
        self.n_classes = n_classes
        self.bilinear = bilinear
        self.n_ch = 256

        self.inc = DoubleConv(n_channels, self.n_ch)
        self.up1 = Up_(self.n_ch, self.n_ch//2, bilinear=True)
        self.up2 = Up_(self.n_ch//2, self.n_ch//4, bilinear)
        self.up3 = Up_(self.n_ch//4, self.n_ch//8, bilinear)
        self.up4 = Up_(self.n_ch//8, self.n_ch//16, bilinear)
        self.reshape = nn.Sequential(
            nn.Conv2d(self.n_ch//16, self.n_ch//16, kernel_size=5, dilation=3),
            nn.BatchNorm2d(self.n_ch//16),
            nn.LeakyReLU(inplace=True),
            nn.Conv2d(self.n_ch//16, self.n_ch//16, kernel_size=5, dilation=3),
            nn.BatchNorm2d(self.n_ch//16),
            nn.LeakyReLU(inplace=True),
            nn.Conv2d(self.n_ch//16, self.n_ch//8, kernel_size=3, dilation=2),
            nn.BatchNorm2d(self.n_ch//8),
            nn.LeakyReLU(inplace=True),
            nn.Conv2d(self.n_ch//8, 32, kernel_size=3, padding=1),
            nn.BatchNorm2d(32),
            nn.LeakyReLU(inplace=True))
        self.outc = OutConv(32, n_classes)

    def forward(self, x):
        x = self.inc(x)
        x = self.up1(x)
        x = self.up2(x)
        x = F.max_pool2d(x, (2,1))
        x = self.up3(x)
        x = self.up4(x)
        x = self.reshape(x) 
        out = self.outc(x)
        return out


class UNetHalf8to100_stack2(nn.Module):
    "16 layers here, input is not added noise, just stack noise and resized mixture"
    def __init__(self, n_channels, n_classes, bilinear=False):
        """Only the up part of the unet
        Args:
            n_channels ([type]): [how many input channels=n_sources]
            n_classes ([type]): [how many output classes=n_sources]
            bilinear (bool, optional): [use interpolation or deconv]. Defaults to False(use deconv).
        """
        super(UNetHalf8to100_stack2, self).__init__()
        self.n_ch = n_channels
        self.n_classes = n_classes
        self.bilinear = bilinear
        self.n_ch = 128

        self.inc = DoubleConv(n_channels, self.n_ch)
        self.up1 = Up_(self.n_ch, self.n_ch//2, bilinear=True)
        self.up2 = Up_(self.n_ch//2, self.n_ch//4, bilinear)
        self.up3 = Up_(self.n_ch//4, self.n_ch//8, bilinear)
        self.up4 = Up_(self.n_ch//8, self.n_ch//16, bilinear)
        self.reshape = nn.Sequential(
            nn.MaxPool2d((2,1)),
            nn.Conv2d(self.n_ch//16, self.n_ch//16, kernel_size=5, dilation=3),
            nn.BatchNorm2d(self.n_ch//16),
            nn.LeakyReLU(inplace=True),
            nn.Conv2d(self.n_ch//16, self.n_ch//16, kernel_size=5, dilation=3),
            nn.BatchNorm2d(self.n_ch//16),
            nn.LeakyReLU(inplace=True),
            nn.Conv2d(self.n_ch//16, self.n_ch//8, kernel_size=3, dilation=2),
            nn.BatchNorm2d(self.n_ch//8),
            nn.LeakyReLU(inplace=True),
            nn.Conv2d(self.n_ch//8, 32, kernel_size=3, padding=1),
            nn.BatchNorm2d(32),
            nn.LeakyReLU(inplace=True))
        self.outc = OutConv(32, n_classes)

    def forward(self, x):
        x = self.inc(x)
        x = self.up1(x)
        x = self.up2(x)
        x = self.up3(x)
        x = self.up4(x)
        x = self.reshape(x) 
        out = self.outc(x)
        return out


class UNetHalf8to100_stack2_256(nn.Module):
    "16 layers here, input is not added noise, just stack noise and resized mixture"
    def __init__(self, n_channels, n_classes, bilinear=False):
        """Only the up part of the unet
        Args:
            n_channels ([type]): [how many input channels=n_sources]
            n_classes ([type]): [how many output classes=n_sources]
            bilinear (bool, optional): [use interpolation or deconv]. Defaults to False(use deconv).
        """
        super(UNetHalf8to100_stack2_256, self).__init__()
        self.n_ch = n_channels
        self.n_classes = n_classes
        self.bilinear = bilinear
        self.n_ch = 256

        self.inc = DoubleConv(n_channels, self.n_ch)
        self.up1 = Up_(self.n_ch, self.n_ch//2, bilinear=True)
        self.up2 = Up_(self.n_ch//2, self.n_ch//4, bilinear)
        self.up3 = Up_(self.n_ch//4, self.n_ch//8, bilinear)
        self.up4 = Up_(self.n_ch//8, self.n_ch//16, bilinear)
        self.reshape = nn.Sequential(
            nn.MaxPool2d((2,1)),
            nn.Conv2d(self.n_ch//16, self.n_ch//16, kernel_size=5, dilation=3),
            nn.BatchNorm2d(self.n_ch//16),
            nn.LeakyReLU(inplace=True),
            nn.Conv2d(self.n_ch//16, self.n_ch//16, kernel_size=5, dilation=3),
            nn.BatchNorm2d(self.n_ch//16),
            nn.LeakyReLU(inplace=True),
            nn.Conv2d(self.n_ch//16, self.n_ch//8, kernel_size=3, dilation=2),
            nn.BatchNorm2d(self.n_ch//8),
            nn.LeakyReLU(inplace=True),
            nn.Conv2d(self.n_ch//8, 32, kernel_size=3, padding=1),
            nn.BatchNorm2d(32),
            nn.LeakyReLU(inplace=True))
        self.outc = OutConv(32, n_classes)

    def forward(self, x):
        x = self.inc(x)
        x = self.up1(x)
        x = self.up2(x)
        x = self.up3(x)
        x = self.up4(x)
        x = self.reshape(x) 
        out = self.outc(x)
        return out


class UNetHalf8to100_256(nn.Module):
    "16 layers here"
    def __init__(self, n_channels, n_classes, bilinear=False):
        """Only the up part of the unet
        Args:
            n_channels ([type]): [how many input channels=n_sources]
            n_classes ([type]): [how many output classes=n_sources]
            bilinear (bool, optional): [use interpolation or deconv]. Defaults to False(use deconv).
        """
        super(UNetHalf8to100_256, self).__init__()
        self.n_ch = n_channels
        self.n_classes = n_classes
        self.bilinear = bilinear
        self.n_ch = 256

        self.inc = DoubleConv(n_channels, self.n_ch)
        self.up1 = Up_(self.n_ch, self.n_ch//2, bilinear=True)
        self.up2 = Up_(self.n_ch//2, self.n_ch//4, bilinear)
        self.up3 = Up_(self.n_ch//4, self.n_ch//8, bilinear)
        self.up4 = Up_(self.n_ch//8, self.n_ch//16, bilinear)
        self.reshape = nn.Sequential(
            nn.Conv2d(self.n_ch//16, self.n_ch//16, kernel_size=5, dilation=3),
            nn.BatchNorm2d(self.n_ch//16),
            nn.LeakyReLU(inplace=True),
            nn.Conv2d(self.n_ch//16, self.n_ch//16, kernel_size=5, dilation=3),
            nn.BatchNorm2d(self.n_ch//16),
            nn.LeakyReLU(inplace=True),
            nn.Conv2d(self.n_ch//16, self.n_ch//8, kernel_size=3, dilation=2),
            nn.BatchNorm2d(self.n_ch//8),
            nn.LeakyReLU(inplace=True),
            nn.Conv2d(self.n_ch//8, 32, kernel_size=3, padding=1),
            nn.BatchNorm2d(32),
            nn.LeakyReLU(inplace=True))
        self.outc = OutConv(32, n_classes)

    def forward(self, x):
        x = self.inc(x)
        x = self.up1(x)
        x = self.up2(x)
        x = self.up3(x)
        x = self.up4(x)
        x = self.reshape(x) 
        out = self.outc(x)
        return out


class UNetHalf8to100_256_sig(nn.Module):
    "16 layers here"
    def __init__(self, n_channels, n_classes, bilinear=False):
        """Only the up part of the unet
        Args:
            n_channels ([type]): [how many input channels=n_sources]
            n_classes ([type]): [how many output classes=n_sources]
            bilinear (bool, optional): [use interpolation or deconv]. Defaults to False(use deconv).
        """
        super(UNetHalf8to100_256, self).__init__()
        self.n_ch = n_channels
        self.n_classes = n_classes
        self.bilinear = bilinear
        self.n_ch = 256

        self.inc = DoubleConv(n_channels, self.n_ch)
        self.up1 = Up_(self.n_ch, self.n_ch//2, bilinear=True)
        self.up2 = Up_(self.n_ch//2, self.n_ch//4, bilinear)
        self.up3 = Up_(self.n_ch//4, self.n_ch//8, bilinear)
        self.up4 = Up_(self.n_ch//8, self.n_ch//16, bilinear)
        self.reshape = nn.Sequential(
            nn.Conv2d(self.n_ch//16, self.n_ch//16, kernel_size=5, dilation=3),
            nn.BatchNorm2d(self.n_ch//16),
            nn.LeakyReLU(inplace=True),
            nn.Conv2d(self.n_ch//16, self.n_ch//16, kernel_size=5, dilation=3),
            nn.BatchNorm2d(self.n_ch//16),
            nn.LeakyReLU(inplace=True),
            nn.Conv2d(self.n_ch//16, self.n_ch//8, kernel_size=3, dilation=2),
            nn.BatchNorm2d(self.n_ch//8),
            nn.LeakyReLU(inplace=True),
            nn.Conv2d(self.n_ch//8, 32, kernel_size=3, padding=1),
            nn.BatchNorm2d(32),
            nn.LeakyReLU(inplace=True))
        self.outc = OutConv(32, n_classes)
        self.sig = nn.Sigmoid()

    def forward(self, x):
        x = self.inc(x)
        x = self.up1(x)
        x = self.up2(x)
        x = self.up3(x)
        x = self.up4(x)
        x = self.reshape(x) 
        x = self.outc(x)
        out = self.sig(x)
        return out


class UNetHalf8to100_256_stack1(nn.Module):
    "16 layers here"
    def __init__(self, n_channels, n_classes, bilinear=False):
        """Only the up part of the unet
        Args:
            n_channels ([type]): [how many input channels=n_sources]
            n_classes ([type]): [how many output classes=n_sources]
            bilinear (bool, optional): [use interpolation or deconv]. Defaults to False(use deconv).
        """
        super(UNetHalf8to100_256_stack1, self).__init__()
        self.n_ch = n_channels
        self.n_classes = n_classes
        self.bilinear = bilinear
        self.n_ch = 256

        self.inc = DoubleConv(n_channels, self.n_ch)
        self.conv = nn.Sequential(
            nn.Conv2d(128, 64, kernel_size=3, padding=(1,0)),
            nn.BatchNorm2d(64),
            nn.LeakyReLU(inplace=True),
            nn.Conv2d(64, 128, kernel_size=3, padding=1),
            nn.BatchNorm2d(128),
            nn.LeakyReLU(inplace=True) )
        self.up1 = Up_(self.n_ch, self.n_ch//2, bilinear=True)
        self.up2 = Up_(self.n_ch//2, self.n_ch//4, bilinear)
        self.up3 = Up_(self.n_ch//4, self.n_ch//8, bilinear)
        self.up4 = Up_(self.n_ch//8, self.n_ch//16, bilinear)
        self.reshape = nn.Sequential(
            nn.Conv2d(self.n_ch//16, self.n_ch//16, kernel_size=5, dilation=3),
            nn.BatchNorm2d(self.n_ch//16),
            nn.LeakyReLU(inplace=True),
            nn.Conv2d(self.n_ch//16, self.n_ch//16, kernel_size=5, dilation=3),
            nn.BatchNorm2d(self.n_ch//16),
            nn.LeakyReLU(inplace=True),
            nn.Conv2d(self.n_ch//16, self.n_ch//8, kernel_size=3, dilation=2),
            nn.BatchNorm2d(self.n_ch//8),
            nn.LeakyReLU(inplace=True),
            nn.Conv2d(self.n_ch//8, 32, kernel_size=3, padding=1),
            nn.BatchNorm2d(32),
            nn.LeakyReLU(inplace=True))
        self.outc = OutConv(32, n_classes)

    def forward(self, x):
        x = self.inc(x)
        x = self.up1(x)
        x = self.conv(x)
        x = self.up2(x)
        x = self.up3(x)
        x = self.up4(x)
        x = self.reshape(x) 
        out = self.outc(x)
        return out


class UNetHalf8to100_stack3(nn.Module):
    "16 layers here, input is not added noise, just stack noise and resized mixture"
    def __init__(self, n_channels, n_classes, bilinear=False):
        """Only the up part of the unet
        Args:
            n_channels ([type]): [how many input channels=n_sources]
            n_classes ([type]): [how many output classes=n_sources]
            bilinear (bool, optional): [use interpolation or deconv]. Defaults to False(use deconv).
        """
        super(UNetHalf8to100_stack3, self).__init__()
        self.n_ch = n_channels
        self.n_classes = n_classes
        self.bilinear = bilinear
        self.n_ch = 128

        self.inc = DoubleConv(n_channels, self.n_ch)
        self.up1 = Up_(self.n_ch, self.n_ch//2, bilinear=True)
        self.up2 = Up_(self.n_ch//2, self.n_ch//4, bilinear)
        self.up3 = Up_(self.n_ch//4, self.n_ch//8, bilinear)
        self.up4 = Up_(self.n_ch//8, self.n_ch//16, bilinear)
        self.reshape = nn.Sequential(
            nn.Conv2d(self.n_ch//16, self.n_ch//16, kernel_size=5, dilation=3, stride=(1,2)),
            nn.BatchNorm2d(self.n_ch//16),
            nn.LeakyReLU(inplace=True),
            nn.Conv2d(self.n_ch//16, self.n_ch//16, kernel_size=5, dilation=(3,4)),
            nn.BatchNorm2d(self.n_ch//16),
            nn.LeakyReLU(inplace=True),
            nn.Conv2d(self.n_ch//16, self.n_ch//8, kernel_size=3, dilation=2),
            nn.BatchNorm2d(self.n_ch//8),
            nn.LeakyReLU(inplace=True),
            nn.Conv2d(self.n_ch//8, 32, kernel_size=3, padding=(1,0)),
            nn.BatchNorm2d(32),
            nn.LeakyReLU(inplace=True))
        self.outc = OutConv(32, n_classes)

    def forward(self, x):
        x = self.inc(x)
        x = self.up1(x)
        x = self.up2(x)
        x = self.up3(x)
        x = self.up4(x)
        x = self.reshape(x) 
        out = self.outc(x)
        return out


class UNetHalf8to100_stack3_256(nn.Module):
    "16 layers here, input is not added noise, just stack noise and resized mixture"
    def __init__(self, n_channels, n_classes, bilinear=False):
        """Only the up part of the unet
        Args:
            n_channels ([type]): [how many input channels=n_sources]
            n_classes ([type]): [how many output classes=n_sources]
            bilinear (bool, optional): [use interpolation or deconv]. Defaults to False(use deconv).
        """
        super(UNetHalf8to100_stack3_256, self).__init__()
        self.n_ch = n_channels
        self.n_classes = n_classes
        self.bilinear = bilinear
        self.n_ch = 128

        self.inc = DoubleConv(n_channels, self.n_ch)
        self.up1 = Up_(self.n_ch, self.n_ch//2, bilinear=True)
        self.up2 = Up_(self.n_ch//2, self.n_ch//4, bilinear)
        self.up3 = Up_(self.n_ch//4, self.n_ch//8, bilinear)
        self.up4 = Up_(self.n_ch//8, self.n_ch//16, bilinear)
        self.reshape = nn.Sequential(
            nn.Conv2d(self.n_ch//16, self.n_ch//16, kernel_size=5, dilation=3, stride=(1,2)),
            nn.BatchNorm2d(self.n_ch//16),
            nn.LeakyReLU(inplace=True),
            nn.Conv2d(self.n_ch//16, self.n_ch//16, kernel_size=5, dilation=(3,4)),
            nn.BatchNorm2d(self.n_ch//16),
            nn.LeakyReLU(inplace=True),
            nn.Conv2d(self.n_ch//16, self.n_ch//8, kernel_size=3, dilation=2),
            nn.BatchNorm2d(self.n_ch//8),
            nn.LeakyReLU(inplace=True),
            nn.Conv2d(self.n_ch//8, 32, kernel_size=3, padding=(1,0)),
            nn.BatchNorm2d(32),
            nn.LeakyReLU(inplace=True))
        self.outc = OutConv(32, n_classes)

    def forward(self, x):
        x = self.inc(x)
        x = self.up1(x)
        x = self.up2(x)
        x = self.up3(x)
        x = self.up4(x)
        x = self.reshape(x) 
        out = self.outc(x)
        return out


class UNetHalf8to100_19(nn.Module):
    "16 layers here"
    def __init__(self, n_channels, n_classes, bilinear=False):
        """Only the up part of the unet
        Args:
            n_channels ([type]): [how many input channels=n_sources]
            n_classes ([type]): [how many output classes=n_sources]
            bilinear (bool, optional): [use interpolation or deconv]. Defaults to False(use deconv).
        """
        super(UNetHalf8to100_19, self).__init__()
        self.n_ch = n_channels
        self.n_classes = n_classes
        self.bilinear = bilinear
        self.n_ch = 128

        self.inc = DoubleConv(n_channels, self.n_ch)
        self.up1 = Up_(self.n_ch, self.n_ch//2, bilinear=True)
        self.up2 = Up_(self.n_ch//2, self.n_ch//4, bilinear)
        self.up3 = Up_(self.n_ch//4, self.n_ch//8, bilinear)
        self.up4 = Up_(self.n_ch//8, self.n_ch//16, bilinear)
        self.reshape = nn.Sequential(
            nn.Conv2d(self.n_ch//16, self.n_ch//16, kernel_size=5, dilation=3),
            nn.BatchNorm2d(self.n_ch//16),
            nn.LeakyReLU(inplace=True),
            nn.Conv2d(self.n_ch//16, self.n_ch//16, kernel_size=5, dilation=3),
            nn.BatchNorm2d(self.n_ch//16),
            nn.LeakyReLU(inplace=True),
            nn.Conv2d(self.n_ch//16, self.n_ch//8, kernel_size=3, dilation=2),
            nn.BatchNorm2d(self.n_ch//8),
            nn.LeakyReLU(inplace=True),
            nn.Conv2d(self.n_ch//8, self.n_ch//8, kernel_size=3, padding=1),
            nn.BatchNorm2d(self.n_ch//8),
            nn.LeakyReLU(inplace=True),
            nn.Conv2d(self.n_ch//8, self.n_ch//8, kernel_size=3, padding=1),
            nn.BatchNorm2d(self.n_ch//8),
            nn.LeakyReLU(inplace=True),
            nn.Conv2d(self.n_ch//8, self.n_ch//8, kernel_size=3, padding=1),
            nn.BatchNorm2d(self.n_ch//8),
            nn.LeakyReLU(inplace=True),
            nn.Conv2d(self.n_ch//8, 32, kernel_size=3, padding=1),
            nn.BatchNorm2d(32),
            nn.LeakyReLU(inplace=True))
        self.outc = OutConv(32, n_classes)

    def forward(self, x):
        x = self.inc(x)
        x = self.up1(x)
        x = self.up2(x)
        x = self.up3(x)
        x = self.up4(x)
        x = self.reshape(x) 
        out = self.outc(x)
        return out


class UNetHalf16to100(nn.Module):
    "14 layers here"
    def __init__(self, n_channels, n_classes, bilinear=False):
        """Only the up part of the unet
        Args:
            n_channels ([type]): [how many input channels=n_sources]
            n_classes ([type]): [how many output classes=n_sources]
            bilinear (bool, optional): [use interpolation or deconv]. Defaults to False(use deconv).
        """
        super(UNetHalf16to100, self).__init__()
        self.n_ch = n_channels
        self.n_classes = n_classes
        self.bilinear = bilinear
        self.n_ch = 128

        self.inc = DoubleConv(n_channels, self.n_ch)
        self.up1 = Up_(self.n_ch, self.n_ch//2, bilinear=True)
        self.up2 = Up_(self.n_ch//2, self.n_ch//4, bilinear)
        self.up3 = Up_(self.n_ch//4, self.n_ch//8, bilinear)
        self.reshape = nn.Sequential(
            nn.Conv2d(self.n_ch//8, self.n_ch//16, kernel_size=5, dilation=3),
            nn.BatchNorm2d(self.n_ch//16),
            nn.LeakyReLU(inplace=True),
            nn.Conv2d(self.n_ch//16, self.n_ch//16, kernel_size=5, dilation=3),
            nn.BatchNorm2d(self.n_ch//16),
            nn.LeakyReLU(inplace=True),
            nn.Conv2d(self.n_ch//16, self.n_ch//8, kernel_size=3, dilation=2),
            nn.BatchNorm2d(self.n_ch//8),
            nn.LeakyReLU(inplace=True),
            nn.Conv2d(self.n_ch//8, 32, kernel_size=3, padding=1),
            nn.BatchNorm2d(32),
            nn.LeakyReLU(inplace=True))
        self.outc = OutConv(32, n_classes)
        self.outc = OutConv(32, n_classes)

    def forward(self, x):
        x = self.inc(x)
        x = self.up1(x)
        x = self.up2(x)
        x = self.up3(x)
        x = self.reshape(x) 
        out = self.outc(x)
        return out


# Full UNet shape structure
class UNet8to100(nn.Module):
    "Too large to train"
    def __init__(self, n_channels, n_classes):
        super(UNet8to100, self).__init__()
        self.n_channels = n_channels
        self.n_classes = n_classes
        self.n_ch = 128

        self.inc = DoubleConv(n_channels, self.n_ch)
        self.down1 = Down(self.n_ch, self.n_ch//2)
        self.down2 = Down(self.n_ch//2, self.n_ch//4)
        self.down3 = Down(self.n_ch//4, self.n_ch//8)
        self.trim = nn.Sequential(
            nn.Conv2d(self.n_ch//8, self.n_ch//16, kernel_size=3),
            nn.BatchNorm2d(self.n_ch//16),
            nn.LeakyReLU(inplace=True),
            nn.Conv2d(self.n_ch//16, 1, kernel_size=3),
            nn.BatchNorm2d(1),
            nn.LeakyReLU(inplace=True))            

        self.up1 = MyUp(self.n_ch, self.n_ch//2)
        self.up2 = MyUp(self.n_ch//2, self.n_ch//4)
        self.up3 = MyUp(self.n_ch//4, self.n_ch//8)
        self.up4 = MyUp(self.n_ch//8, self.n_ch//8)
        self.reshape = nn.Sequential(
            nn.MaxPool2d((2,1)),
            nn.Conv2d(self.n_ch//8, self.n_ch//16, kernel_size=5, dilation=3),
            nn.BatchNorm2d(self.n_ch//16),
            nn.LeakyReLU(inplace=True),
            nn.Conv2d(self.n_ch//16, self.n_ch//16, kernel_size=5, dilation=3),
            nn.BatchNorm2d(self.n_ch//16),
            nn.LeakyReLU(inplace=True),
            nn.Conv2d(self.n_ch//16, self.n_ch//8, kernel_size=3, dilation=2),
            nn.BatchNorm2d(self.n_ch//8),
            nn.LeakyReLU(inplace=True),
            nn.Conv2d(self.n_ch//8, 32, kernel_size=3, padding=1),
            nn.BatchNorm2d(32),
            nn.LeakyReLU(inplace=True))
        self.outc = OutConv(32, n_classes)

    def forward(self, x, gamma):
        x1 = self.inc(x)
        x2 = self.down1(x1)
        x3 = self.down2(x2)
        x4 = self.down3(x3)
        x5  = self.trim(x4)
        # stacking x and gamma to have regular larger input size
        x = torch.cat((x5, gamma), dim=-2)
        x = self.inc(x)
        x = self.up1(x)
        x = self.up2(x)
        x = self.up3(x)
        x = self.up4(x)
        x = self.reshape(x)
        out = self.outc(x)
        return out
