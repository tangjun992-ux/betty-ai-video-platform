import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"

const badgeVariants = cva(
  "inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[11px] font-semibold transition-colors backdrop-blur-sm",
  {
    variants: {
      variant: {
        default:
          "bg-accent-cyan/[0.08] text-accent-cyan border border-accent-cyan/20",
        secondary:
          "bg-cosmic-surface text-text-secondary border border-cosmic-border",
        destructive:
          "bg-destructive-muted text-destructive border border-destructive/20",
        success:
          "bg-success-muted text-success border border-success/20",
        warning:
          "bg-warning-muted text-warning border border-warning/20",
        info:
          "bg-info-muted text-info border border-info/20",
        outline:
          "text-text-secondary border border-cosmic-border bg-transparent",
        brand:
          "bg-foreground text-background border border-cosmic-border",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
)

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  )
}

export { Badge, badgeVariants }
