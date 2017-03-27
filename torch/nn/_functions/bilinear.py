import torch
from torch.autograd import Function

class Bilinear(Function):
    
    def forward(self, input1, input2, weight, bias=None):


		self.save_for_backward(input1, input2, weight, bias)
		output = input1.new(input1.size(0), weight.size(0))
		
		self.buff2 = input1.new()
		self.buff2.resize_as_(input2)#.fill_(1)
		
		print "weight 0: ", weight[0]

		# compute output scores:
		#output.resize_(input1.size(0), weight.size(0))
		for k in range(weight.size(0)):
			torch.mm(input1, weight[k], out=self.buff2)
			self.buff2.mul_(input2)
			torch.sum(self.buff2, 1, out=output.narrow(1, k, 1))

		if bias is not None:
			output.add_(bias.view(1, bias.nelement()).expand_as(output))
		print "after output: ",output
		return output

    def backward(self, grad_output):
		input1, input2, weight, bias = self.saved_tensors

		grad_input1 = grad_input2 = grad_weight = grad_bias = None
        
		self.buff1 = input1.new()
		self.buff1.resize_as_(input1)

		grad_input1.resize_as_(input1).fill_(0)
		grad_input2.resize_as_(input2).fill_(0)
        
		if self.needs_input_grad[0]:
			grad_input1 = torch.mm(input2, weight[0].t())
			grad_input1.mul_(grad_output.narrow(1, 0, 1).expand(grad_input1.size(0),
			                                                     grad_input1.size(1)))
			grad_input2 = torch.mm(input1, weight[0])
			grad_input2.mul_(grad_output.narrow(1, 0, 1).expand(grad_input2.size(0),
			                                                     grad_input2.size(1)))

		if self.needs_input_grad[1]:
			#self.buff1 = input1.new()
			#self.buff1.resize_as_(input1)
			# accumulate parameter gradients:
			for k in range(weight.size(0)):
				torch.mul(input1, grad_output.narrow(1, k, 1).expand_as(input1), out=self.buff1)
				grad_weight[k] = torch.mm(self.buff1.t(), input2)
		if bias is not None and self.needs_input_grad[2]:
			#self.buff1 = input1.new()
			#self.buff1.resize_as_(input1)
			grad_bias.add_(scale, grad_output.sum(0))

		if bias is not None:
			return grad_input1, grad_input2, grad_weight, grad_bias
		else:
			return grad_input1, grad_input2, grad_weight
        