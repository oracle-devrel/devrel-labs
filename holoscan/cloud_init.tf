resource local_file cloudinit {
  content = templatefile("${path.module}/cloudinit.sh",
    { 
      PUB_KEY       = var.ssh_public_key,
      nvidia_api_key = var.nvidia_api_key,
  })
  filename        = "${path.module}/cloudinit.sh"
}

data "cloudinit_config" "config" {
	depends_on = [local_file.cloudinit]  
    gzip          = false
    base64_encode = true
    part {
        filename     = "cloudinit.sh"
        content_type = "text/x-shellscript"
        content      = file("${path.module}/cloudinit.sh")
    }
}
